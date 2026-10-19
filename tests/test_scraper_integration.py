"""Prueba de integración opcional contra el sitio real.

No se ejecuta por defecto porque necesita internet y un navegador. Para
activarla:

    Windows PowerShell:
        $env:RUN_INTEGRATION="1"
        pytest tests/test_scraper_integration.py

    macOS/Linux:
        RUN_INTEGRATION=1 pytest tests/test_scraper_integration.py
"""

import os

import pytest

from config import Config
from scraper import scrape_catalog
from sites import BOOKS_TO_SCRAPE

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="Define RUN_INTEGRATION=1 para ejecutar la prueba real.",
)


def test_scrape_catalog_extrae_dos_libros():
    config = Config(limit=2, headless=True, timeout_ms=30_000)

    resultado = scrape_catalog(config, BOOKS_TO_SCRAPE)

    assert len(resultado.libros) == 2
    assert resultado.fallos == []
    assert resultado.libros[0]["titulo"]
    assert resultado.libros[0]["precio_crudo"]
    assert resultado.libros[0]["url"].startswith("https://books.toscrape.com/")
