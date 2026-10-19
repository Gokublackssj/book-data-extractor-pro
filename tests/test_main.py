"""Pruebas offline de la orquestación de main con fichas fallidas."""

from __future__ import annotations

from pathlib import Path

import pytest

import main as main_module
from scraper import FalloExtraccion, ScrapeResult

LIBRO_CRUDO = {
    "titulo": "Libro válido",
    "precio_crudo": "£10.00",
    "disp_cruda": "In stock",
    "url": "https://example.test/libro",
}


def test_main_reporta_fallos_y_exporta_exitosos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fallo = FalloExtraccion(
        pagina=1,
        url_pagina="https://example.test/catalogo",
        indice=2,
        mensaje="selector roto",
    )
    monkeypatch.setattr(
        main_module,
        "scrape_catalog",
        lambda config, perfil: ScrapeResult([LIBRO_CRUDO], [fallo]),
    )

    with caplog.at_level("INFO"):
        codigo = main_module.main(
            [
                "--limit",
                "2",
                "--output-dir",
                str(tmp_path),
                "--format",
                "csv",
            ]
        )

    assert codigo == 0
    assert "Fichas extraídas: 1 | Fichas fallidas: 1" in caplog.text
    assert (
        "Se exportarán solo los libros extraídos correctamente (1)."
        in caplog.text
    )

    archivos = list(tmp_path.glob("*.csv"))
    assert len(archivos) == 1
    contenido = archivos[0].read_text(encoding="utf-8-sig")
    assert "Libro válido" in contenido


def test_main_no_exporta_si_todas_fallan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fallo = FalloExtraccion(
        pagina=1,
        url_pagina="https://example.test/catalogo",
        indice=1,
        mensaje="selector roto",
    )
    monkeypatch.setattr(
        main_module,
        "scrape_catalog",
        lambda config, perfil: ScrapeResult([], [fallo]),
    )

    with caplog.at_level("INFO"):
        codigo = main_module.main(
            [
                "--output-dir",
                str(tmp_path),
                "--format",
                "csv",
            ]
        )

    assert codigo == 1
    assert "Fichas extraídas: 0 | Fichas fallidas: 1" in caplog.text
    assert "No se pudo extraer ningún libro" in caplog.text
    assert list(tmp_path.glob("*")) == []


def test_main_avisa_si_truncado_por_max_pages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        main_module,
        "scrape_catalog",
        lambda config, perfil: ScrapeResult(
            [LIBRO_CRUDO],
            [],
            paginas=1,
            truncado_por_max_pages=True,
        ),
    )

    with caplog.at_level("INFO"):
        codigo = main_module.main(
            [
                "--max-pages",
                "1",
                "--output-dir",
                str(tmp_path),
                "--format",
                "csv",
            ]
        )

    assert codigo == 0
    assert "Páginas recorridas: 1" in caplog.text
    assert "La extracción puede estar incompleta" in caplog.text
    assert "--max-pages=1" in caplog.text
    assert len(list(tmp_path.glob("*.csv"))) == 1


def test_main_no_avisa_si_no_truncado(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        main_module,
        "scrape_catalog",
        lambda config, perfil: ScrapeResult(
            [LIBRO_CRUDO],
            [],
            paginas=1,
            truncado_por_max_pages=False,
        ),
    )

    with caplog.at_level("INFO"):
        codigo = main_module.main(
            [
                "--max-pages",
                "2",
                "--output-dir",
                str(tmp_path),
                "--format",
                "csv",
            ]
        )

    assert codigo == 0
    assert "Páginas recorridas: 1" in caplog.text
    assert "La extracción puede estar incompleta" not in caplog.text
