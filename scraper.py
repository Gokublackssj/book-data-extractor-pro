"""Extracción del catálogo con Playwright.

Responsabilidad única: abrir el navegador, recorrer páginas y devolver
registros crudos. La limpieza y la exportación viven en otros módulos.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from urllib.parse import urljoin

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Locator,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from config import Config
from sites import SiteProfile

logger = logging.getLogger(__name__)


class ScraperError(RuntimeError):
    """Error fatal durante la extracción."""


@dataclass(frozen=True)
class FalloExtraccion:
    """Datos mínimos de una ficha que no se pudo extraer."""

    pagina: int
    url_pagina: str
    indice: int
    mensaje: str


@dataclass
class ScrapeResult:
    """Resultado completo de una extracción.

    ``paginas`` cuenta las páginas visitadas. ``truncado_por_max_pages`` es
    ``True`` solo si se alcanzó ``max_pages`` y existía una página siguiente.
    """

    libros: list[dict]
    fallos: list[FalloExtraccion]
    paginas: int = 0
    truncado_por_max_pages: bool = False


def _resumen_error(exc: Exception, maximo: int = 300) -> str:
    """Devuelve una primera línea corta, sin volcar todo el error de Playwright."""

    lineas = str(exc).strip().splitlines()
    detalle = lineas[0].strip() if lineas else ""
    if len(detalle) > maximo:
        detalle = detalle[:maximo].rstrip() + "..."
    return detalle or "sin detalle"


def _comando_playwright(argumentos: str) -> str:
    """Construye un comando copiable usando el Python que ejecuta el programa."""

    return f'"{sys.executable}" -m playwright {argumentos}'


def _mensaje_error_lanzamiento(exc: Exception) -> str:
    """Traduce un fallo de Playwright a un mensaje accionable en español."""

    detalle = _resumen_error(exc)
    texto = detalle.casefold()

    if (
        "executable doesn't exist" in texto
        or "executable does not exist" in texto
        or "playwright install" in texto
    ):
        return (
            "No se pudo iniciar Chromium porque el navegador no está instalado. "
            f"Ejecuta: {_comando_playwright('install chromium')}"
        )

    if "missing dependencies" in texto or "install-deps" in texto:
        return (
            "No se pudo iniciar Chromium porque faltan dependencias del sistema. "
            f"En Linux, ejecuta: {_comando_playwright('install-deps chromium')}"
        )

    return (
        "No se pudo iniciar Chromium. Revisa la instalación de Playwright y vuelve "
        "a intentarlo. Puedes reinstalarlo con: "
        f"{_comando_playwright('install chromium')}. Detalle: {detalle}"
    )


def _mensaje_error_recurso(exc: Exception, accion: str) -> str:
    """Mensaje para fallos al crear contexto, página o configurar la espera."""

    return (
        f"No se pudo {accion}: {_resumen_error(exc)}. "
        "Cierra otras instancias de Chromium y vuelve a intentarlo. "
        "Si el problema continúa, reinstala el navegador con: "
        f"{_comando_playwright('install chromium')}"
    )


def _cerrar_recursos(
    context: BrowserContext | None,
    browser: Browser | None,
) -> None:
    """Cierra lo que haya llegado a crearse, sin ocultar el error original."""

    if context is not None:
        try:
            context.close()
        except Exception:
            logger.debug(
                "No se pudo cerrar el contexto de Playwright",
                exc_info=True,
            )

    if browser is not None:
        try:
            browser.close()
        except Exception:
            logger.debug(
                "No se pudo cerrar el navegador de Playwright",
                exc_info=True,
            )


def _iniciar_navegador(
    playwright: Playwright,
    config: Config,
) -> tuple[Browser, BrowserContext, Page]:
    """Inicia Chromium y prepara contexto y página.

    Si algo falla después de crear un recurso, se cierra lo que ya exista.
    """

    browser: Browser | None = None
    context: BrowserContext | None = None

    try:
        try:
            browser = playwright.chromium.launch(
                headless=config.headless,
                slow_mo=config.slow_mo,
            )
        except (PlaywrightError, OSError) as exc:
            raise ScraperError(_mensaje_error_lanzamiento(exc)) from exc

        try:
            context = browser.new_context(
                user_agent=config.user_agent,
                viewport={"width": 1280, "height": 900},
            )
        except (PlaywrightError, OSError) as exc:
            raise ScraperError(
                _mensaje_error_recurso(
                    exc,
                    "crear el contexto del navegador",
                )
            ) from exc

        try:
            page = context.new_page()
        except (PlaywrightError, OSError) as exc:
            raise ScraperError(
                _mensaje_error_recurso(
                    exc,
                    "abrir la pestaña del navegador",
                )
            ) from exc

        try:
            page.set_default_timeout(config.timeout_ms)
        except (PlaywrightError, OSError) as exc:
            raise ScraperError(
                _mensaje_error_recurso(
                    exc,
                    "configurar el tiempo de espera de la página",
                )
            ) from exc

        return browser, context, page
    except BaseException:
        # Incluye KeyboardInterrupt: si el usuario cancela el arranque,
        # cerramos lo que ya se haya creado antes de propagar la excepción.
        _cerrar_recursos(context, browser)
        raise


def _texto(contenedor: Locator, selector: str) -> str:
    """Devuelve el texto del primer elemento que coincide, o cadena vacía."""

    localizador = contenedor.locator(selector)
    if localizador.count() == 0:
        return ""
    return (localizador.first.inner_text() or "").strip()


def _extraer_libro(
    articulo: Locator,
    url_pagina: str,
    perfil: SiteProfile,
) -> dict:
    """Extrae un producto usando los selectores del perfil."""

    titulo_loc = articulo.locator(perfil.title_selector)
    if titulo_loc.count() == 0:
        titulo = ""
    else:
        primero = titulo_loc.first
        if perfil.title_attribute:
            titulo = (
                primero.get_attribute(perfil.title_attribute)
                or primero.inner_text()
                or ""
            ).strip()
        else:
            titulo = (primero.inner_text() or "").strip()

    enlace = articulo.locator(perfil.link_selector)
    href = ""
    if enlace.count() > 0:
        href = (
            enlace.first.get_attribute(perfil.link_attribute) or ""
        ).strip()

    url = urljoin(url_pagina, href) if href else ""

    return {
        "titulo": titulo,
        "precio_crudo": (
            _texto(articulo, perfil.price_selector)
            if perfil.price_selector
            else ""
        ),
        "disp_cruda": (
            _texto(articulo, perfil.availability_selector)
            if perfil.availability_selector
            else ""
        ),
        "url": url,
    }


def _cargar_pagina(
    page: Page,
    url: str,
    config: Config,
    perfil: SiteProfile,
) -> None:
    """Navega y espera a que los productos estén visibles.

    No usamos ``time.sleep``: Playwright espera al selector, que es una
    condición real de la página. Si la página no tiene resultados, el timeout
    se captura y el bucle decide qué hacer.
    """

    logger.info("Cargando %s", url)
    page.goto(url, wait_until="domcontentloaded", timeout=config.timeout_ms)

    try:
        page.locator(perfil.product_selector).first.wait_for(
            state="visible",
            timeout=config.timeout_ms,
        )
    except PlaywrightTimeoutError:
        logger.warning(
            "No aparecieron productos con el selector %r en %s",
            perfil.product_selector,
            url,
        )


def _siguiente_url(
    page: Page,
    url_actual: str,
    perfil: SiteProfile,
) -> str | None:
    """Devuelve la URL de la página siguiente, o None si no existe."""

    if not perfil.next_page_selector:
        return None

    enlace = page.locator(perfil.next_page_selector)
    if enlace.count() == 0:
        return None

    href = enlace.first.get_attribute(perfil.next_page_attribute)
    if not href:
        return None

    return urljoin(url_actual, href)


def scrape_catalog(config: Config, perfil: SiteProfile) -> ScrapeResult:
    """Recorre el catálogo y devuelve libros y fichas fallidas.

    ``perfil`` define qué selectores CSS usar. El motor es el mismo para
    cualquier sitio con estructura de catálogo y paginación por enlace.
    """

    libros: list[dict] = []
    fallos: list[FalloExtraccion] = []
    paginas = 0
    truncado_por_max_pages = False

    try:
        with sync_playwright() as playwright:
            browser, context, page = _iniciar_navegador(playwright, config)

            try:
                url_actual: str | None = config.url
                visitadas: set[str] = set()

                while url_actual and paginas < config.max_pages:
                    if url_actual in visitadas:
                        logger.warning(
                            "La paginación volvió a una URL ya visitada: %s",
                            url_actual,
                        )
                        break
                    visitadas.add(url_actual)
                    paginas += 1

                    _cargar_pagina(page, url_actual, config, perfil)
                    articulos = page.locator(perfil.product_selector)
                    cantidad = articulos.count()

                    if cantidad == 0:
                        logger.warning(
                            "No se encontraron libros en la página %d: %s",
                            paginas,
                            url_actual,
                        )
                        break

                    logger.info("Página %d: %d libros encontrados", paginas, cantidad)

                    for indice in range(cantidad):
                        if config.limit is not None and len(libros) >= config.limit:
                            break
                        try:
                            libros.append(
                                _extraer_libro(
                                    articulos.nth(indice),
                                    url_actual,
                                    perfil,
                                )
                            )
                        except Exception as exc:  # Un libro roto no debe tumbar todo.
                            fallo = FalloExtraccion(
                                pagina=paginas,
                                url_pagina=url_actual,
                                indice=indice + 1,
                                mensaje=_resumen_error(exc),
                            )
                            fallos.append(fallo)
                            logger.warning(
                                "No se pudo extraer la ficha %d de la página %d "
                                "(%s): %s",
                                fallo.indice,
                                fallo.pagina,
                                fallo.url_pagina,
                                fallo.mensaje,
                            )

                    if config.limit is not None and len(libros) >= config.limit:
                        break

                    siguiente = _siguiente_url(page, url_actual, perfil)
                    if not siguiente:
                        logger.info("No hay más páginas.")
                        break

                    if paginas >= config.max_pages:
                        # Hay una página siguiente, pero el límite de seguridad
                        # impide visitarla: la extracción puede estar incompleta.
                        truncado_por_max_pages = True
                        break

                    # Pausa cortés entre páginas para no martillar el servidor.
                    page.wait_for_timeout(config.delay_ms)
                    url_actual = siguiente

            except PlaywrightTimeoutError as exc:
                raise ScraperError(
                    "Tiempo de espera agotado al cargar el catálogo: "
                    f"{_resumen_error(exc)}"
                ) from exc
            except ScraperError:
                raise
            except Exception as exc:
                raise ScraperError(
                    "Error inesperado durante el scraping: "
                    f"{_resumen_error(exc)}"
                ) from exc
            finally:
                _cerrar_recursos(context, browser)

    except ScraperError:
        raise
    except (PlaywrightError, OSError) as exc:
        raise ScraperError(_mensaje_error_lanzamiento(exc)) from exc
    except Exception as exc:
        raise ScraperError(
            "No se pudo iniciar Playwright o Chromium. "
            f"{_resumen_error(exc)}. Revisa la instalación de Playwright y vuelve "
            "a intentarlo. Puedes reinstalar Chromium con: "
            f"{_comando_playwright('install chromium')}"
        ) from exc

    if config.limit is not None:
        libros = libros[: config.limit]

    return ScrapeResult(
        libros=libros,
        fallos=fallos,
        paginas=paginas,
        truncado_por_max_pages=truncado_por_max_pages,
    )


def scrape_books(config: Config, perfil: SiteProfile) -> list[dict]:
    """API compatible: devuelve solo los libros extraídos."""

    return scrape_catalog(config, perfil).libros
