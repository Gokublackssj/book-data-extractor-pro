"""Pruebas offline de extracción, fallos, arranque y limpieza de Playwright."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from playwright.sync_api import Error as PlaywrightError

import main as main_module
import scraper
from config import Config
from scraper import (
    FalloExtraccion,
    ScraperError,
    ScrapeResult,
    _iniciar_navegador,
    scrape_books,
    scrape_catalog,
)
from sites import BOOKS_TO_SCRAPE


class FakePage:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.timeout: int | None = None

    def set_default_timeout(self, timeout: int) -> None:
        if self.error is not None:
            raise self.error
        self.timeout = timeout


class FakeContext:
    def __init__(
        self,
        page: FakePage | None = None,
        error: Exception | None = None,
    ) -> None:
        self.page = page if page is not None else FakePage()
        self.error = error
        self.closed = False

    def new_page(self) -> FakePage:
        if self.error is not None:
            raise self.error
        return self.page

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(
        self,
        context: FakeContext | None = None,
        error: Exception | None = None,
    ) -> None:
        self.context = context if context is not None else FakeContext()
        self.error = error
        self.closed = False

    def new_context(self, **kwargs: object) -> FakeContext:
        if self.error is not None:
            raise self.error
        return self.context

    def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(
        self,
        browser: FakeBrowser | None = None,
        error: Exception | None = None,
    ) -> None:
        self.browser = browser
        self.error = error

    def launch(self, **kwargs: object) -> FakeBrowser:
        if self.error is not None:
            raise self.error
        if self.browser is None:
            self.browser = FakeBrowser()
        return self.browser


class FakePlaywright:
    def __init__(self, chromium: FakeChromium) -> None:
        self.chromium = chromium


class FakeSyncPlaywright:
    def __init__(self, playwright: FakePlaywright) -> None:
        self.playwright = playwright

    def __enter__(self) -> FakePlaywright:
        return self.playwright

    def __exit__(self, *args: object) -> bool:
        return False


class FailingSyncPlaywright:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def __enter__(self) -> None:
        raise self.error

    def __exit__(self, *args: object) -> bool:
        return False


class ErrorAlCerrarContexto(FakeContext):
    def close(self) -> None:
        self.closed = True
        raise PlaywrightError("fallo al cerrar el contexto")


class FakeArticulo:
    def __init__(self, indice: int) -> None:
        self.indice = indice


class FakeArticulos:
    def __init__(self, cantidad: int) -> None:
        self.cantidad = cantidad

    def count(self) -> int:
        return self.cantidad

    def nth(self, indice: int) -> FakeArticulo:
        return FakeArticulo(indice)


class FakeCatalogPage(FakePage):
    def __init__(self, cantidad: int) -> None:
        super().__init__()
        self.cantidad = cantidad

    def locator(self, selector: str) -> FakeArticulos:
        return FakeArticulos(self.cantidad)

    def wait_for_timeout(self, timeout: int) -> None:
        pass


def _preparar_extraccion_falsa(
    monkeypatch: pytest.MonkeyPatch,
    page: FakePage,
    extraer: Callable[..., dict],
    siguiente: Callable[..., str | None] | None = None,
) -> None:
    context = FakeContext(page=page)
    browser = FakeBrowser(context=context)
    chromium = FakeChromium(browser=browser)
    monkeypatch.setattr(
        scraper,
        "sync_playwright",
        lambda: FakeSyncPlaywright(FakePlaywright(chromium)),
    )
    monkeypatch.setattr(scraper, "_cargar_pagina", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        scraper,
        "_siguiente_url",
        siguiente or (lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(scraper, "_extraer_libro", extraer)


def _extraer_libro_simple(articulo, url_pagina, perfil):
    return {
        "titulo": f"Libro {url_pagina} {articulo.indice}",
        "precio_crudo": "",
        "disp_cruda": "",
        "url": url_pagina,
    }


def test_scrape_catalog_registra_fallo_con_contexto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = FakeCatalogPage(cantidad=2)

    def extraer(articulo, url_pagina, perfil):
        if articulo.indice == 1:
            raise ValueError("selector roto\nsegunda línea")
        return {
            "titulo": "Libro válido",
            "precio_crudo": "£10.00",
            "disp_cruda": "In stock",
            "url": "https://example.test/libro",
        }

    _preparar_extraccion_falsa(monkeypatch, page, extraer)

    resultado = scrape_catalog(
        Config(url="https://example.test/catalogo", limit=None),
        BOOKS_TO_SCRAPE,
    )

    assert isinstance(resultado, ScrapeResult)
    assert len(resultado.libros) == 1
    assert resultado.libros[0]["titulo"] == "Libro válido"
    assert resultado.fallos == [
        FalloExtraccion(
            pagina=1,
            url_pagina="https://example.test/catalogo",
            indice=2,
            mensaje="selector roto",
        )
    ]


def test_scrape_catalog_registra_fallo_en_pagina_siguiente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = FakeCatalogPage(cantidad=2)
    siguientes = iter(["https://example.test/catalogo/2", None])

    def siguiente(*args, **kwargs):
        return next(siguientes)

    def extraer(articulo, url_pagina, perfil):
        if url_pagina.endswith("/2") and articulo.indice == 0:
            raise RuntimeError("fallo en segunda página")
        return {
            "titulo": f"Libro {url_pagina} {articulo.indice}",
            "precio_crudo": "",
            "disp_cruda": "",
            "url": url_pagina,
        }

    _preparar_extraccion_falsa(monkeypatch, page, extraer, siguiente)

    resultado = scrape_catalog(
        Config(url="https://example.test/catalogo/1", limit=None),
        BOOKS_TO_SCRAPE,
    )

    assert len(resultado.libros) == 3
    assert len(resultado.fallos) == 1
    fallo = resultado.fallos[0]
    assert fallo.pagina == 2
    assert fallo.url_pagina == "https://example.test/catalogo/2"
    assert fallo.indice == 1
    assert fallo.mensaje == "fallo en segunda página"


def test_scrape_books_mantiene_retorno_de_lista(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = FakeCatalogPage(cantidad=1)

    def extraer(articulo, url_pagina, perfil):
        return {
            "titulo": "Libro",
            "precio_crudo": "",
            "disp_cruda": "",
            "url": url_pagina,
        }

    _preparar_extraccion_falsa(monkeypatch, page, extraer)

    libros = scrape_books(
        Config(url="https://example.test/catalogo", limit=None),
        BOOKS_TO_SCRAPE,
    )

    assert isinstance(libros, list)
    assert len(libros) == 1
    assert libros[0]["titulo"] == "Libro"


def test_max_pages_sin_siguiente_no_marca_truncamiento(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = FakeCatalogPage(cantidad=1)
    siguientes = iter(["https://example.test/catalogo/2", None])

    def siguiente(*args, **kwargs):
        return next(siguientes)

    _preparar_extraccion_falsa(
        monkeypatch,
        page,
        _extraer_libro_simple,
        siguiente,
    )

    with caplog.at_level("WARNING"):
        resultado = scrape_catalog(
            Config(
                url="https://example.test/catalogo/1",
                limit=None,
                max_pages=2,
            ),
            BOOKS_TO_SCRAPE,
        )

    assert resultado.paginas == 2
    assert resultado.truncado_por_max_pages is False
    assert "max-pages" not in caplog.text


def test_max_pages_con_siguiente_marca_truncamiento(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = FakeCatalogPage(cantidad=1)

    def siguiente(*args, **kwargs):
        return "https://example.test/catalogo/siguiente"

    _preparar_extraccion_falsa(
        monkeypatch,
        page,
        _extraer_libro_simple,
        siguiente,
    )

    resultado = scrape_catalog(
        Config(url="https://example.test/catalogo/1", limit=None, max_pages=2),
        BOOKS_TO_SCRAPE,
    )

    assert resultado.paginas == 2
    assert resultado.truncado_por_max_pages is True


def test_limit_sin_limite_respeta_max_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = FakeCatalogPage(cantidad=1)

    def siguiente(*args, **kwargs):
        return "https://example.test/catalogo/siguiente"

    _preparar_extraccion_falsa(
        monkeypatch,
        page,
        _extraer_libro_simple,
        siguiente,
    )

    resultado = scrape_catalog(
        Config(url="https://example.test/catalogo/1", limit=None, max_pages=1),
        BOOKS_TO_SCRAPE,
    )

    assert len(resultado.libros) == 1
    assert resultado.paginas == 1
    assert resultado.truncado_por_max_pages is True


def test_limit_finito_no_marca_truncamiento_por_paginas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = FakeCatalogPage(cantidad=3)

    def siguiente(*args, **kwargs):
        return "https://example.test/catalogo/2"

    _preparar_extraccion_falsa(
        monkeypatch,
        page,
        _extraer_libro_simple,
        siguiente,
    )

    resultado = scrape_catalog(
        Config(url="https://example.test/catalogo/1", limit=1, max_pages=1),
        BOOKS_TO_SCRAPE,
    )

    assert len(resultado.libros) == 1
    assert resultado.paginas == 1
    assert resultado.truncado_por_max_pages is False


def test_lanzamiento_sin_navegador_indica_como_instalarlo() -> None:
    chromium = FakeChromium(
        error=PlaywrightError(
            "Executable doesn't exist at C:/ms-playwright/chromium/chrome.exe"
        )
    )

    with pytest.raises(ScraperError) as excinfo:
        _iniciar_navegador(FakePlaywright(chromium), Config())

    mensaje = str(excinfo.value)
    assert "No se pudo iniciar Chromium" in mensaje
    assert "playwright install chromium" in mensaje
    assert "Traceback" not in mensaje


def test_lanzamiento_con_dependencias_faltantes_indica_comando_linux() -> None:
    chromium = FakeChromium(
        error=PlaywrightError("Host system is missing dependencies to run browsers")
    )

    with pytest.raises(ScraperError) as excinfo:
        _iniciar_navegador(FakePlaywright(chromium), Config())

    mensaje = str(excinfo.value)
    assert "faltan dependencias del sistema" in mensaje
    assert "playwright install-deps chromium" in mensaje


def test_error_al_crear_contexto_cierra_browser() -> None:
    browser = FakeBrowser(error=PlaywrightError("fallo al crear contexto"))
    playwright = FakePlaywright(FakeChromium(browser=browser))

    with pytest.raises(ScraperError, match="crear el contexto del navegador"):
        _iniciar_navegador(playwright, Config())

    assert browser.closed


def test_error_al_abrir_pagina_cierra_contexto_y_browser() -> None:
    context = FakeContext(error=PlaywrightError("fallo al abrir página"))
    browser = FakeBrowser(context=context)
    playwright = FakePlaywright(FakeChromium(browser=browser))

    with pytest.raises(ScraperError, match="abrir la pestaña del navegador"):
        _iniciar_navegador(playwright, Config())

    assert context.closed
    assert browser.closed


def test_error_al_configurar_timeout_cierra_contexto_y_browser() -> None:
    page = FakePage(error=PlaywrightError("fallo al configurar timeout"))
    context = FakeContext(page=page)
    browser = FakeBrowser(context=context)
    playwright = FakePlaywright(FakeChromium(browser=browser))

    with pytest.raises(ScraperError, match="configurar el tiempo de espera"):
        _iniciar_navegador(playwright, Config())

    assert context.closed
    assert browser.closed


def test_inicio_correcto_devuelve_recursos_abiertos() -> None:
    page = FakePage()
    context = FakeContext(page=page)
    browser = FakeBrowser(context=context)
    playwright = FakePlaywright(FakeChromium(browser=browser))
    config = Config()

    browser_creado, context_creado, page_creada = _iniciar_navegador(
        playwright,
        config,
    )

    assert browser_creado is browser
    assert context_creado is context
    assert page_creada is page
    assert page.timeout == config.timeout_ms
    assert not browser.closed
    assert not context.closed


def test_cierre_con_error_no_oculta_el_fallo_original() -> None:
    context = ErrorAlCerrarContexto(
        error=PlaywrightError("fallo al abrir página")
    )
    browser = FakeBrowser(context=context)
    playwright = FakePlaywright(FakeChromium(browser=browser))

    with pytest.raises(ScraperError, match="abrir la pestaña del navegador"):
        _iniciar_navegador(playwright, Config())

    assert context.closed
    assert browser.closed


def test_interrupcion_durante_inicio_cierra_contexto_y_browser() -> None:
    context = FakeContext(error=KeyboardInterrupt())
    browser = FakeBrowser(context=context)
    playwright = FakePlaywright(FakeChromium(browser=browser))

    with pytest.raises(KeyboardInterrupt):
        _iniciar_navegador(playwright, Config())

    assert context.closed
    assert browser.closed


def test_scrape_books_convierte_error_de_sync_playwright(monkeypatch) -> None:
    error = PlaywrightError("Executable doesn't exist at C:/ms-playwright")
    monkeypatch.setattr(
        scraper,
        "sync_playwright",
        lambda: FailingSyncPlaywright(error),
    )

    with pytest.raises(ScraperError, match="playwright install chromium"):
        scrape_books(Config(), BOOKS_TO_SCRAPE)


def test_scrape_books_convierte_error_de_lanzamiento(monkeypatch) -> None:
    chromium = FakeChromium(
        error=PlaywrightError("Executable doesn't exist at C:/ms-playwright")
    )
    monkeypatch.setattr(
        scraper,
        "sync_playwright",
        lambda: FakeSyncPlaywright(FakePlaywright(chromium)),
    )

    with pytest.raises(ScraperError, match="playwright install chromium"):
        scrape_books(Config(), BOOKS_TO_SCRAPE)


def test_main_muestra_error_controlado_sin_traceback(
    monkeypatch,
    caplog,
) -> None:
    def fallar(config: Config, perfil: object) -> list[dict]:
        raise ScraperError(
            "No se pudo iniciar Chromium. Ejecuta: playwright install chromium"
        )

    monkeypatch.setattr(main_module, "scrape_catalog", fallar)

    with caplog.at_level("ERROR"):
        codigo = main_module.main(["--limit", "1"])

    assert codigo == 1
    assert "No se pudo iniciar Chromium" in caplog.text
    assert "Traceback" not in caplog.text
