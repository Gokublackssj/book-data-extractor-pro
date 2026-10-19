"""Configuración central del proyecto.

Aquí viven los valores por defecto. La línea de comandos (main.py) puede
sobrescribirlos sin necesidad de editar este archivo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# --- Valores por defecto -------------------------------------------------

DEFAULT_URL = "https://books.toscrape.com/"
DEFAULT_LIMIT = 20
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_PREFIX = "libros"
DEFAULT_TIMEOUT_MS = 20_000
DEFAULT_MAX_PAGES = 50
DEFAULT_DELAY_MS = 500

# Un user-agent honesto identifica la herramienta. No imitamos a un navegador
# real para ocultar el scraping.
DEFAULT_USER_AGENT = "BookDataExtractorPro/1.0"

# --- Contrato de datos ---------------------------------------------------

# Clave interna -> nombre de columna visible en Excel/CSV.
# Mantener este mapeo en un solo lugar evita que el scraper, la limpieza y el
# exportador se desincronicen.
COLUMNS: dict[str, str] = {
    "titulo": "Título",
    "precio": "Precio",
    "moneda": "Moneda",
    "disponibilidad": "Disponibilidad",
    "url": "URL",
    "advertencias": "Advertencias",
}

COLUMN_ORDER: tuple[str, ...] = tuple(COLUMNS)


@dataclass(frozen=True)
class Config:
    """Configuración inmutable de una ejecución."""

    url: str = DEFAULT_URL
    limit: int | None = DEFAULT_LIMIT
    output_dir: Path = field(default_factory=lambda: Path(DEFAULT_OUTPUT_DIR))
    prefix: str = DEFAULT_PREFIX
    headless: bool = True
    slow_mo: int = 0
    timeout_ms: int = DEFAULT_TIMEOUT_MS
    max_pages: int = DEFAULT_MAX_PAGES
    delay_ms: int = DEFAULT_DELAY_MS
    user_agent: str = DEFAULT_USER_AGENT
    csv_delimiter: str = ","
    export_format: str = "both"  # "both" | "csv" | "xlsx"

    def __post_init__(self) -> None:
        # Permite construir Config(output_dir="output") además de con Path.
        object.__setattr__(self, "output_dir", Path(self.output_dir))

        if self.limit is not None:
            if self.limit < 0:
                raise ValueError("limit no puede ser negativo.")
            if self.limit == 0:
                # 0 es la forma cómoda de decir "sin límite" desde la CLI.
                object.__setattr__(self, "limit", None)
        if self.timeout_ms <= 0:
            raise ValueError("timeout_ms debe ser mayor que 0.")
        if self.max_pages <= 0:
            raise ValueError("max_pages debe ser mayor que 0.")
        if self.slow_mo < 0 or self.delay_ms < 0:
            raise ValueError("Los retardos no pueden ser negativos.")
        if len(self.csv_delimiter) != 1:
            raise ValueError("csv_delimiter debe ser un solo carácter.")
        if self.export_format not in {"both", "csv", "xlsx"}:
            raise ValueError("export_format debe ser 'both', 'csv' o 'xlsx'.")
