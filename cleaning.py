"""Limpieza y validación de los datos extraídos.

Este módulo no sabe nada de Playwright ni de Excel: recibe diccionarios y
devuelve diccionarios. Eso permite probarlo sin internet y sin navegador.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlsplit, urlunsplit

# Busca el primer número dentro de un texto como "Â£51.77" o "12,99 €".
# El signo es opcional para poder rechazar precios negativos.
_NUMERO_RE = re.compile(r"[-+]?\d[\d.,]*")

_SIMBOLOS_MONEDA = ("£", "$", "€", "¥")
_CODIGOS_MONEDA = {
    "GBP": "£",
    "USD": "$",
    "EUR": "€",
    "JPY": "¥",
}

_CENTIMOS = Decimal("0.01")


def _normalizar_numero(numero: str) -> str | None:
    """Convierte un número con separadores locales a formato decimal.

    Ejemplos:
        "1,234.56" -> "1234.56"
        "1.234,56" -> "1234.56"
        "12,99"    -> "12.99"
        "1.234"    -> "1234"     (tres dígitos finales = miles)
        "51.77"    -> "51.77"
    """

    if not numero:
        return None

    tiene_coma = "," in numero
    tiene_punto = "." in numero

    if tiene_coma and tiene_punto:
        # El último separador que aparece es el decimal.
        if numero.rfind(",") > numero.rfind("."):
            numero = numero.replace(".", "").replace(",", ".")
        else:
            numero = numero.replace(",", "")
    elif tiene_coma:
        parte_decimal = numero.rsplit(",", 1)[1]
        if len(parte_decimal) in (1, 2):
            numero = numero.replace(",", ".")
        else:
            numero = numero.replace(",", "")
    elif tiene_punto:
        parte_decimal = numero.rsplit(".", 1)[1]
        if len(parte_decimal) == 3:
            # "1.234" se interpreta como miles, no como 1.234 unidades.
            numero = numero.replace(".", "")

    return numero


def parsear_precio(precio_crudo: str | None) -> Decimal | None:
    """Devuelve el precio como Decimal o None si no se puede interpretar."""

    if not precio_crudo:
        return None

    coincidencia = _NUMERO_RE.search(str(precio_crudo))
    if not coincidencia:
        return None

    numero = _normalizar_numero(coincidencia.group(0))
    if not numero:
        return None

    try:
        precio = Decimal(numero)
    except (InvalidOperation, ValueError):
        return None

    if precio < 0:
        return None

    return precio.quantize(_CENTIMOS, rounding=ROUND_HALF_UP)


def detectar_moneda(precio_crudo: str | None) -> str:
    """Conserva el símbolo original de la moneda, sin convertirlo."""

    if not precio_crudo:
        return ""

    texto = str(precio_crudo)

    for simbolo in _SIMBOLOS_MONEDA:
        if simbolo in texto:
            return simbolo

    texto_mayusculas = texto.upper()
    for codigo, simbolo in _CODIGOS_MONEDA.items():
        if codigo in texto_mayusculas:
            return simbolo

    return ""


def extraer_precio_y_moneda(
    precio_crudo: str | None,
) -> tuple[Decimal | None, str]:
    """Separa el valor numérico del símbolo de moneda.

    No convierte divisas: 10 £ siguen siendo 10 £.
    """

    return parsear_precio(precio_crudo), detectar_moneda(precio_crudo)


def normalizar_disponibilidad(disp_cruda: str | None) -> str:
    """Normaliza el texto de disponibilidad a tres estados conocidos."""

    if not disp_cruda:
        return "desconocida"

    texto = str(disp_cruda).casefold()

    # Primero "agotado": "out of stock" no contiene "in stock", pero este
    # orden deja la intención clara y evita falsos positivos.
    if "out of stock" in texto or "agotado" in texto or "sin stock" in texto:
        return "agotado"
    if "in stock" in texto or "disponible" in texto:
        return "disponible"

    return "desconocida"


def limpiar_libro(libro_crudo: dict) -> dict:
    """Convierte un registro crudo en un registro limpio y validado.

    No elimina filas con problemas: las conserva con campos vacíos y una
    lista de advertencias. Así el usuario sabe qué falló en lugar de perder
    datos en silencio.
    """

    titulo = (libro_crudo.get("titulo") or "").strip()
    url = (libro_crudo.get("url") or "").strip()
    precio, moneda = extraer_precio_y_moneda(libro_crudo.get("precio_crudo"))
    disponibilidad = normalizar_disponibilidad(libro_crudo.get("disp_cruda"))

    advertencias: list[str] = []

    if not titulo:
        advertencias.append("título vacío")
    if not url:
        advertencias.append("URL vacía")
    if precio is None:
        advertencias.append("precio ausente o inválido")
    if not moneda:
        advertencias.append("moneda desconocida")
    if disponibilidad == "desconocida":
        if libro_crudo.get("disp_cruda"):
            advertencias.append("disponibilidad no reconocida")
        else:
            advertencias.append("disponibilidad ausente")

    return {
        "titulo": titulo,
        "precio": precio,
        "moneda": moneda,
        "disponibilidad": disponibilidad,
        "url": url,
        "advertencias": advertencias,
    }


def limpiar_libros(libros_crudos: Iterable[dict]) -> list[dict]:
    """Limpia una colección de registros crudos."""

    return [limpiar_libro(libro) for libro in libros_crudos]


def _normalizar_url(url: str) -> str:
    """Normaliza una URL para comparar duplicados, no para mostrarla."""

    url = (url or "").strip()
    if not url:
        return ""

    partes = urlsplit(url)
    if not partes.scheme or not partes.netloc:
        return url.rstrip("/")

    ruta = partes.path.rstrip("/")
    return urlunsplit(
        (
            partes.scheme.lower(),
            partes.netloc.lower(),
            ruta,
            partes.query,
            "",  # El fragmento (#...) no identifica al producto.
        )
    )


def _clave_deduplicacion(libro: dict) -> tuple | None:
    """Devuelve una clave estable para detectar duplicados.

    Preferimos la URL. Si no existe, usamos título + precio + moneda. Si
    tampoco hay título, devolvemos None para no borrar filas sin identidad.
    """

    url = _normalizar_url(libro.get("url", ""))
    if url:
        return ("url", url)

    titulo = (libro.get("titulo") or "").strip().casefold()
    if titulo:
        return (
            "titulo",
            titulo,
            str(libro.get("precio")),
            libro.get("moneda", ""),
        )

    return None


def eliminar_duplicados(libros: Iterable[dict]) -> tuple[list[dict], int]:
    """Elimina duplicados conservando el orden original.

    Devuelve (libros_unicos, cantidad_eliminada).
    """

    lista = list(libros)
    vistos: set[tuple] = set()
    unicos: list[dict] = []

    for libro in lista:
        clave = _clave_deduplicacion(libro)
        if clave is not None:
            if clave in vistos:
                continue
            vistos.add(clave)
        unicos.append(libro)

    return unicos, len(lista) - len(unicos)
