"""Perfiles de sitio: los selectores que cambian de una web a otra.

El motor de scraping es genérico, pero los selectores CSS son específicos de
cada sitio. Un perfil agrupa esos selectores para no tenerlos hardcodeados en
``scraper.py``.

Un perfil se puede definir en Python (como ``BOOKS_TO_SCRAPE``) o cargar desde
un archivo JSON con ``--profile``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path
from urllib.parse import urlparse

from config import DEFAULT_URL


def _texto(valor: object) -> str:
    return "" if valor is None else str(valor).strip()


@dataclass(frozen=True)
class SiteProfile:
    """Selectores y URL inicial de un catálogo."""

    name: str
    start_url: str
    product_selector: str
    title_selector: str
    description: str = ""
    title_attribute: str | None = None
    price_selector: str = ""
    availability_selector: str = ""
    link_selector: str = ""
    link_attribute: str = "href"
    next_page_selector: str = ""
    next_page_attribute: str = "href"

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _texto(self.name))
        object.__setattr__(self, "start_url", _texto(self.start_url))
        object.__setattr__(
            self, "product_selector", _texto(self.product_selector)
        )
        object.__setattr__(self, "title_selector", _texto(self.title_selector))
        object.__setattr__(self, "description", _texto(self.description))
        object.__setattr__(
            self, "title_attribute", _texto(self.title_attribute) or None
        )
        object.__setattr__(self, "price_selector", _texto(self.price_selector))
        object.__setattr__(
            self,
            "availability_selector",
            _texto(self.availability_selector),
        )
        object.__setattr__(
            self,
            "link_selector",
            _texto(self.link_selector) or _texto(self.title_selector),
        )
        object.__setattr__(
            self, "link_attribute", _texto(self.link_attribute) or "href"
        )
        object.__setattr__(
            self, "next_page_selector", _texto(self.next_page_selector)
        )
        object.__setattr__(
            self,
            "next_page_attribute",
            _texto(self.next_page_attribute) or "href",
        )

        if not self.name:
            raise ValueError("El perfil necesita un nombre.")
        if not self.product_selector:
            raise ValueError(
                f"El perfil '{self.name}' necesita product_selector."
            )
        if not self.title_selector:
            raise ValueError(
                f"El perfil '{self.name}' necesita title_selector."
            )

        partes = urlparse(self.start_url)
        if partes.scheme not in {"http", "https"} or not partes.netloc:
            raise ValueError(
                f"start_url inválida en el perfil '{self.name}': "
                f"{self.start_url!r}"
            )

    @classmethod
    def from_dict(cls, data: dict) -> "SiteProfile":
        """Crea un perfil desde un diccionario y detecta errores de escritura."""

        if not isinstance(data, dict):
            raise ValueError("El perfil debe ser un objeto JSON.")

        permitidos = {campo.name for campo in fields(cls)}
        desconocidos = sorted(set(data) - permitidos)
        if desconocidos:
            raise ValueError(
                "Campos desconocidos en el perfil: " + ", ".join(desconocidos)
            )

        try:
            return cls(**data)
        except TypeError as exc:
            raise ValueError(
                f"Faltan campos obligatorios en el perfil: {exc}"
            ) from exc


BOOKS_TO_SCRAPE = SiteProfile(
    name="books_toscrape",
    description="Catálogo de práctica de libros (Books to Scrape).",
    start_url=DEFAULT_URL,
    product_selector="article.product_pod",
    title_selector="h3 a",
    title_attribute="title",
    price_selector=".price_color",
    availability_selector=".instock.availability",
    link_selector="h3 a",
    link_attribute="href",
    next_page_selector="li.next a",
    next_page_attribute="href",
)

SITES: dict[str, SiteProfile] = {BOOKS_TO_SCRAPE.name: BOOKS_TO_SCRAPE}


def load_profile(path: str | Path) -> SiteProfile:
    """Carga un perfil desde un archivo JSON."""

    ruta = Path(path)

    try:
        texto = ruta.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(
            f"No se encontró el archivo de perfil: {ruta}"
        ) from exc
    except OSError as exc:
        raise ValueError(f"No se pudo leer el perfil {ruta}: {exc}") from exc

    try:
        data = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"El perfil {ruta} no es JSON válido: {exc}"
        ) from exc

    return SiteProfile.from_dict(data)


def get_site_profile(
    name: str | None = None,
    profile_path: str | Path | None = None,
) -> SiteProfile:
    """Devuelve un perfil integrado o carga uno desde JSON."""

    if name and profile_path:
        raise ValueError("Usa --site o --profile, no ambos a la vez.")

    if profile_path:
        return load_profile(profile_path)

    clave = name or BOOKS_TO_SCRAPE.name
    try:
        return SITES[clave]
    except KeyError as exc:
        disponibles = ", ".join(sorted(SITES))
        raise ValueError(
            f"Perfil desconocido: {clave}. Disponibles: {disponibles}."
        ) from exc
