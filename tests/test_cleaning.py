"""Pruebas de las funciones puras de limpieza."""

from decimal import Decimal

import pytest

from cleaning import (
    eliminar_duplicados,
    extraer_precio_y_moneda,
    limpiar_libro,
    normalizar_disponibilidad,
)


@pytest.mark.parametrize(
    ("entrada", "precio_esperado", "moneda_esperada"),
    [
        ("£51.77", Decimal("51.77"), "£"),
        ("Â£51.77", Decimal("51.77"), "£"),
        ("$1,234.56", Decimal("1234.56"), "$"),
        ("12,99 €", Decimal("12.99"), "€"),
        ("1.234,56", Decimal("1234.56"), ""),
        ("1,234", Decimal("1234.00"), ""),
        ("51.7", Decimal("51.70"), ""),
        ("£0.00", Decimal("0.00"), "£"),
        ("", None, ""),
        (None, None, ""),
        ("sin precio", None, ""),
        ("£abc", None, "£"),
        ("-5.00", None, ""),
    ],
)
def test_extraer_precio_y_moneda(entrada, precio_esperado, moneda_esperada):
    assert extraer_precio_y_moneda(entrada) == (precio_esperado, moneda_esperada)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("In Stock (22 available)", "disponible"),
        ("In stock", "disponible"),
        ("Disponible", "disponible"),
        ("Out of stock", "agotado"),
        ("Sin stock", "agotado"),
        ("Agotado", "agotado"),
        ("", "desconocida"),
        (None, "desconocida"),
        ("Texto raro", "desconocida"),
    ],
)
def test_normalizar_disponibilidad(entrada, esperado):
    assert normalizar_disponibilidad(entrada) == esperado


def test_limpiar_libro_completo():
    crudo = {
        "titulo": "  Un libro increíble  ",
        "precio_crudo": "Â£51.77",
        "disp_cruda": "In Stock (22 available)",
        "url": "https://books.toscrape.com/catalogue/un-libro_1/index.html",
    }

    libro = limpiar_libro(crudo)

    assert libro["titulo"] == "Un libro increíble"
    assert libro["precio"] == Decimal("51.77")
    assert libro["moneda"] == "£"
    assert libro["disponibilidad"] == "disponible"
    assert libro["url"] == crudo["url"]
    assert libro["advertencias"] == []


def test_limpiar_libro_con_nulos_no_falla():
    libro = limpiar_libro(
        {
            "titulo": None,
            "precio_crudo": None,
            "disp_cruda": None,
            "url": None,
        }
    )

    assert libro["titulo"] == ""
    assert libro["precio"] is None
    assert libro["moneda"] == ""
    assert libro["disponibilidad"] == "desconocida"
    assert "título vacío" in libro["advertencias"]
    assert "URL vacía" in libro["advertencias"]


def test_precio_cero_no_se_trata_como_ausente():
    libro = limpiar_libro(
        {
            "titulo": "Libro gratis",
            "precio_crudo": "£0.00",
            "disp_cruda": "In Stock",
            "url": "https://example.com/libro",
        }
    )

    assert libro["precio"] == Decimal("0.00")
    assert "precio ausente o inválido" not in libro["advertencias"]


def test_eliminar_duplicados_por_url_y_conserva_orden():
    libros = [
        {
            "titulo": "A",
            "precio": Decimal("1.00"),
            "moneda": "£",
            "disponibilidad": "disponible",
            "url": "https://example.com/libro/1",
            "advertencias": [],
        },
        {
            "titulo": "A duplicado",
            "precio": Decimal("1.00"),
            "moneda": "£",
            "disponibilidad": "disponible",
            "url": "https://example.com/libro/1/",
            "advertencias": [],
        },
        {
            "titulo": "B",
            "precio": Decimal("2.00"),
            "moneda": "£",
            "disponibilidad": "disponible",
            "url": "https://example.com/libro/2",
            "advertencias": [],
        },
    ]

    unicos, eliminados = eliminar_duplicados(libros)

    assert len(unicos) == 2
    assert eliminados == 1
    assert [libro["titulo"] for libro in unicos] == ["A", "B"]


def test_eliminar_duplicados_sin_url_usa_titulo_y_precio():
    libros = [
        {
            "titulo": "Mismo",
            "precio": Decimal("10.00"),
            "moneda": "£",
            "disponibilidad": "disponible",
            "url": "",
            "advertencias": [],
        },
        {
            "titulo": "Mismo",
            "precio": Decimal("10.00"),
            "moneda": "£",
            "disponibilidad": "disponible",
            "url": "",
            "advertencias": [],
        },
        {
            "titulo": "Distinto",
            "precio": Decimal("10.00"),
            "moneda": "£",
            "disponibilidad": "disponible",
            "url": "",
            "advertencias": [],
        },
    ]

    unicos, eliminados = eliminar_duplicados(libros)

    assert len(unicos) == 2
    assert eliminados == 1


def test_filas_sin_titulo_ni_url_no_se_borran_entre_si():
    libros = [
        {
            "titulo": "",
            "precio": None,
            "moneda": "",
            "disponibilidad": "desconocida",
            "url": "",
            "advertencias": ["título vacío"],
        },
        {
            "titulo": "",
            "precio": None,
            "moneda": "",
            "disponibilidad": "desconocida",
            "url": "",
            "advertencias": ["título vacío"],
        },
    ]

    unicos, eliminados = eliminar_duplicados(libros)

    assert len(unicos) == 2
    assert eliminados == 0
