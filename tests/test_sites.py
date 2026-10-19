"""Pruebas de los perfiles de sitio."""

import json

import pytest

from sites import (
    BOOKS_TO_SCRAPE,
    SITES,
    SiteProfile,
    get_site_profile,
    load_profile,
)


def _perfil_json(**cambios):
    datos = {
        "name": "ejemplo",
        "description": "Catálogo de ejemplo",
        "start_url": "https://example.com/catalogo",
        "product_selector": ".producto",
        "title_selector": "h2",
        "title_attribute": None,
        "price_selector": ".precio",
        "availability_selector": ".stock",
        "link_selector": "a",
        "link_attribute": "href",
        "next_page_selector": "a.siguiente",
        "next_page_attribute": "href",
    }
    datos.update(cambios)
    return datos


def test_perfil_integrado_existe():
    assert "books_toscrape" in SITES
    assert BOOKS_TO_SCRAPE.product_selector == "article.product_pod"
    assert BOOKS_TO_SCRAPE.next_page_selector == "li.next a"


def test_link_selector_usa_title_selector_por_defecto():
    perfil = SiteProfile(
        name="ejemplo",
        start_url="https://example.com",
        product_selector=".producto",
        title_selector="h2",
    )

    assert perfil.link_selector == "h2"
    assert perfil.link_attribute == "href"
    assert perfil.next_page_selector == ""


def test_start_url_invalida():
    with pytest.raises(ValueError):
        SiteProfile(
            name="ejemplo",
            start_url="ftp://example.com",
            product_selector=".producto",
            title_selector="h2",
        )


def test_product_selector_obligatorio():
    with pytest.raises(ValueError):
        SiteProfile(
            name="ejemplo",
            start_url="https://example.com",
            product_selector="",
            title_selector="h2",
        )


def test_title_selector_obligatorio():
    with pytest.raises(ValueError):
        SiteProfile(
            name="ejemplo",
            start_url="https://example.com",
            product_selector=".producto",
            title_selector="",
        )


def test_campo_desconocido_falla():
    with pytest.raises(ValueError):
        SiteProfile.from_dict(_perfil_json(selector_typo=".algo"))


def test_faltan_campos_obligatorios():
    with pytest.raises(ValueError):
        SiteProfile.from_dict(
            {
                "name": "incompleto",
                "start_url": "https://example.com",
            }
        )


def test_cargar_perfil_desde_json(tmp_path):
    ruta = tmp_path / "perfil.json"
    ruta.write_text(json.dumps(_perfil_json()), encoding="utf-8")

    perfil = load_profile(ruta)

    assert perfil.name == "ejemplo"
    assert perfil.title_selector == "h2"
    assert perfil.link_selector == "a"
    assert perfil.next_page_selector == "a.siguiente"


def test_json_invalido_falla(tmp_path):
    ruta = tmp_path / "perfil.json"
    ruta.write_text("{esto no es json", encoding="utf-8")

    with pytest.raises(ValueError):
        load_profile(ruta)


def test_get_site_profile_integrado():
    assert get_site_profile("books_toscrape").name == "books_toscrape"
    assert get_site_profile().name == "books_toscrape"


def test_get_site_profile_desconocido():
    with pytest.raises(ValueError):
        get_site_profile("no_existe")


def test_no_se_puede_usar_site_y_profile_a_la_vez(tmp_path):
    with pytest.raises(ValueError):
        get_site_profile("books_toscrape", tmp_path / "perfil.json")
