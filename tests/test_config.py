"""Pruebas de la configuración."""

import pytest

from config import Config


def test_limit_cero_significa_sin_limite():
    assert Config(limit=0).limit is None


def test_limit_cero_conserva_max_pages():
    config = Config(limit=0, max_pages=7)
    assert config.limit is None
    assert config.max_pages == 7


def test_limit_negativo_falla():
    with pytest.raises(ValueError):
        Config(limit=-1)


def test_formato_invalido_falla():
    with pytest.raises(ValueError):
        Config(export_format="pdf")


def test_delimitador_debe_ser_un_caracter():
    with pytest.raises(ValueError):
        Config(csv_delimiter=";;")
