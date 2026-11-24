"""Testes do validador de NIF (S1.4)."""

import random

import pytest

from agente_faturas.nucleo.nif import gerar_nif_valido, nif_valido, normalizar_nif

# --- nif_valido -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "nif",
    [
        "123456789",
        "999999990",  # consumidor final; resto 0, por isso o dígito de controlo é 0
        "PT 123 456 789",
        "pt123456789",
        " 123456789 ",
        "123\u00a0456\u00a0789",  # espaço não separável, comum em texto tirado de PDF
    ],
)
def test_nif_valido(nif):
    assert nif_valido(nif)


@pytest.mark.parametrize(
    "nif",
    [
        "123456780",  # dígito de controlo errado
        "12345678",  # 8 dígitos
        "1234567890",  # 10 dígitos
        "12345678a",
        "abcdefghi",
        "",
        "PT",
        "\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19",  # '１２３…' de largura total
    ],
)
def test_nif_invalido(nif):
    assert not nif_valido(nif)


def test_so_verifica_o_digito_de_controlo():
    # Limitação conhecida (D-013): sem regras para o primeiro dígito, 000000000 passa.
    assert nif_valido("000000000")


# --- normalizar_nif --------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto, esperado",
    [("PT 123 456 789", "123456789"), ("pt123456789", "123456789"), ("123456789", "123456789")],
)
def test_normalizar_tira_espacos_e_prefixo(texto, esperado):
    assert normalizar_nif(texto) == esperado


# --- gerar_nif_valido ------------------------------------------------------------------


def test_mil_nif_gerados_sao_validos():
    rng = random.Random(42)
    nifs = [gerar_nif_valido("5", rng) for _ in range(1000)]
    assert all(nif_valido(n) for n in nifs)


def test_nif_gerado_tem_o_prefixo_e_9_digitos():
    nif = gerar_nif_valido("50", random.Random(1))
    assert nif.startswith("50")
    assert len(nif) == 9


def test_mesma_semente_da_os_mesmos_nif():
    rng_a = random.Random(42)
    rng_b = random.Random(42)
    assert [gerar_nif_valido("5", rng_a) for _ in range(10)] == [
        gerar_nif_valido("5", rng_b) for _ in range(10)
    ]


@pytest.mark.parametrize("prefixo", ["", "5a", "123456789"])
def test_prefixo_invalido_da_erro(prefixo):
    with pytest.raises(ValueError):
        gerar_nif_valido(prefixo, random.Random(0))
