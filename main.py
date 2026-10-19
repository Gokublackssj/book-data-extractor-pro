"""Punto de entrada de Book Data Extractor Pro.

Orquesta el flujo completo:
    1. Leer argumentos.
    2. Extraer libros con Playwright.
    3. Limpiar, validar y deduplicar.
    4. Exportar a Excel/CSV.
    5. Mostrar un resumen.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

from cleaning import eliminar_duplicados, limpiar_libros
from config import (
    DEFAULT_DELAY_MS,
    DEFAULT_LIMIT,
    DEFAULT_MAX_PAGES,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PREFIX,
    DEFAULT_TIMEOUT_MS,
    Config,
)
from exporter import ExportError, export_books
from scraper import ScraperError, scrape_catalog
from sites import SITES, get_site_profile

logger = logging.getLogger("book_data_extractor")


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extrae un catálogo de libros a Excel y CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    grupo_sitio = parser.add_mutually_exclusive_group()
    grupo_sitio.add_argument(
        "--site",
        choices=sorted(SITES),
        default=None,
        help="Perfil de sitio integrado.",
    )
    grupo_sitio.add_argument(
        "--profile",
        type=Path,
        default=None,
        help="Archivo JSON con los selectores de un sitio.",
    )
    parser.add_argument(
        "--list-sites",
        action="store_true",
        help="Muestra los perfiles integrados y termina.",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Sobrescribe la URL inicial del perfil.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=(
            "Máximo de libros a extraer. Usa 0 para no limitar la cantidad; "
            "--max-pages sigue aplicando."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Carpeta donde se guardan los archivos.",
    )
    parser.add_argument(
        "--prefix",
        default=DEFAULT_PREFIX,
        help="Prefijo de los archivos de salida.",
    )
    parser.add_argument(
        "--format",
        choices=("both", "xlsx", "csv"),
        default="both",
        dest="export_format",
        help="Formato de salida.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Muestra el navegador. Útil para depurar.",
    )
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=0,
        help="Retardo de Playwright entre acciones, en milisegundos.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_MS,
        help="Tiempo máximo de espera por página, en milisegundos.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="Límite de seguridad de páginas, incluso con --limit 0.",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=DEFAULT_DELAY_MS,
        help="Pausa entre páginas, en milisegundos.",
    )
    parser.add_argument(
        "--csv-delimiter",
        default=",",
        help="Separador del CSV. Usa ';' si tu Excel en español lo necesita.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Muestra mensajes de depuración.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Book Data Extractor Pro 1.0.0",
    )
    return parser


def configurar_consola() -> None:
    """Fuerza UTF-8 en la salida para no romper tildes y símbolos.

    Windows puede usar una codificación local (cp1252) cuando la salida se
    redirige a un archivo o a otra herramienta. Los datos siempre se guardan en
    UTF-8; esto solo afecta a los mensajes de consola.
    """

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def configurar_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )


def validar_url(url: str) -> str:
    partes = urlparse(url)
    if partes.scheme not in {"http", "https"} or not partes.netloc:
        raise ValueError(
            "La URL debe empezar por http:// o https:// y tener un dominio."
        )
    return url


def main(argv: list[str] | None = None) -> int:
    configurar_consola()
    parser = construir_parser()
    args = parser.parse_args(argv)
    configurar_logging(args.verbose)

    if args.list_sites:
        print("Perfiles integrados:")
        for nombre, perfil in sorted(SITES.items()):
            print(f"  {nombre}: {perfil.description} ({perfil.start_url})")
        return 0

    try:
        try:
            perfil = get_site_profile(args.site, args.profile)
        except ValueError as exc:
            parser.error(str(exc))

        url = validar_url(args.url or perfil.start_url)

        if args.limit < 0:
            parser.error(
                "--limit no puede ser negativo. Usa 0 para no limitar los libros; "
                "--max-pages sigue aplicando."
            )
        if args.timeout <= 0:
            parser.error("--timeout debe ser mayor que 0.")
        if args.max_pages <= 0:
            parser.error("--max-pages debe ser mayor que 0.")
        if args.slow_mo < 0 or args.delay < 0:
            parser.error("Los retardos no pueden ser negativos.")
        if len(args.csv_delimiter) != 1:
            parser.error("--csv-delimiter debe ser un solo carácter.")

        config = Config(
            url=url,
            limit=args.limit,
            output_dir=Path(args.output_dir),
            prefix=args.prefix,
            headless=not args.headed,
            slow_mo=args.slow_mo,
            timeout_ms=args.timeout,
            max_pages=args.max_pages,
            delay_ms=args.delay,
            csv_delimiter=args.csv_delimiter,
            export_format=args.export_format,
        )

        limite_texto = (
            "sin límite de libros" if config.limit is None else str(config.limit)
        )
        logger.info("Iniciando extracción de %s", config.url)
        logger.info(
            "Perfil: %s | Límite: %s | Páginas máx.: %d | Formato: %s | "
            "Navegador: %s",
            perfil.name,
            limite_texto,
            config.max_pages,
            config.export_format,
            "visible" if not config.headless else "headless",
        )

        resultado_extraccion = scrape_catalog(config, perfil)
        libros_crudos = resultado_extraccion.libros
        fallos = resultado_extraccion.fallos

        logger.info(
            "Fichas extraídas: %d | Fichas fallidas: %d | Páginas recorridas: %d",
            len(libros_crudos),
            len(fallos),
            resultado_extraccion.paginas,
        )

        if resultado_extraccion.truncado_por_max_pages:
            logger.warning(
                "La extracción puede estar incompleta: se alcanzó --max-pages=%d "
                "y todavía había páginas siguientes. Aumenta --max-pages si "
                "necesitas más.",
                config.max_pages,
            )

        if not libros_crudos:
            if fallos:
                logger.error(
                    "No se pudo extraer ningún libro. "
                    "Todas las fichas encontradas fallaron."
                )
            else:
                logger.error(
                    "No se encontraron libros. Revisa la URL, la conexión o el HTML del sitio."
                )
            return 1

        if fallos:
            logger.warning(
                "Se exportarán solo los libros extraídos correctamente (%d). "
                "Las fichas fallidas no se incluyen en el archivo.",
                len(libros_crudos),
            )

        libros_limpios = limpiar_libros(libros_crudos)
        libros_unicos, duplicados = eliminar_duplicados(libros_limpios)
        con_advertencias = sum(1 for libro in libros_unicos if libro["advertencias"])

        logger.info(
            "Libros en el archivo: %d | Duplicados eliminados: %d | Con advertencias: %d",
            len(libros_unicos),
            duplicados,
            con_advertencias,
        )

        resultado = export_books(libros_unicos, config)

        logger.info("Listo. Archivos generados:")
        if resultado.csv_path:
            logger.info("  CSV:  %s", resultado.csv_path.resolve())
        if resultado.xlsx_path:
            logger.info("  XLSX: %s", resultado.xlsx_path.resolve())
        logger.info("Filas exportadas: %d", resultado.filas)

        return 0

    except (ScraperError, ExportError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        logger.warning("Proceso cancelado por el usuario.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
