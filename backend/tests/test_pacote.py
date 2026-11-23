"""Teste trivial: confirma que o pacote está instalado e que os subpacotes importam."""

import importlib

import pytest

import agente_faturas

SUBPACOTES = ["nucleo", "servicos", "api"]


def test_pacote_importa():
    assert agente_faturas.__doc__


@pytest.mark.parametrize("nome", SUBPACOTES)
def test_subpacote_importa(nome):
    modulo = importlib.import_module(f"agente_faturas.{nome}")
    assert modulo.__name__ == f"agente_faturas.{nome}"
