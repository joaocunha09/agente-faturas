"""Testes das taxas de IVA com vigência (S1.6)."""

from datetime import date
from decimal import Decimal

import pytest
import yaml
from pydantic import ValidationError

from agente_faturas.configuracao import carregar_tabela_iva
from agente_faturas.nucleo.iva import SemTaxaIVA, TabelaIVA
from agente_faturas.nucleo.modelos import Escalao, EspacoFiscal


@pytest.fixture(scope="module")
def tabela() -> TabelaIVA:
    """A tabela real, lida de config/iva.yaml."""
    return carregar_tabela_iva()


def periodo(desde: date, reduzida=6, intermedia=13, normal=23, **outros) -> dict:
    """Um período como vem do YAML, para as tabelas pequenas dos testes."""
    return {
        "desde": desde,
        "reduzida": reduzida,
        "intermedia": intermedia,
        "normal": normal,
        **outros,
    }


# --- Taxas do config/iva.yaml ----------------------------------------------------------


@pytest.mark.parametrize(
    "espaco, escalao, data, esperada",
    [
        # Os casos do "Pronto quando" do PLANO.md
        (EspacoFiscal.PT_AC, Escalao.NORMAL, date(2019, 12, 31), 18),
        (EspacoFiscal.PT_AC, Escalao.NORMAL, date(2026, 11, 23), 16),
        (EspacoFiscal.PT_MA, Escalao.REDUZIDA, date(2024, 9, 30), 5),
        (EspacoFiscal.PT_MA, Escalao.REDUZIDA, date(2024, 10, 1), 4),
        (EspacoFiscal.PT, Escalao.INTERMEDIA, date(2026, 6, 15), 13),
        # Os dois dias à volta da mudança nos Açores
        (EspacoFiscal.PT_AC, Escalao.NORMAL, date(2021, 6, 30), 18),
        (EspacoFiscal.PT_AC, Escalao.NORMAL, date(2021, 7, 1), 16),
        # As outras taxas em vigor hoje
        (EspacoFiscal.PT, Escalao.REDUZIDA, date(2026, 6, 15), 6),
        (EspacoFiscal.PT, Escalao.NORMAL, date(2026, 6, 15), 23),
        (EspacoFiscal.PT_AC, Escalao.REDUZIDA, date(2026, 6, 15), 4),
        (EspacoFiscal.PT_AC, Escalao.INTERMEDIA, date(2026, 6, 15), 9),
        (EspacoFiscal.PT_MA, Escalao.INTERMEDIA, date(2026, 6, 15), 12),
        (EspacoFiscal.PT_MA, Escalao.NORMAL, date(2026, 6, 15), 22),
    ],
)
def test_taxa(tabela, espaco, escalao, data, esperada):
    assert tabela.taxa(espaco, escalao, data) == esperada


def test_taxa_e_decimal(tabela):
    assert isinstance(tabela.taxa(EspacoFiscal.PT, Escalao.NORMAL, date(2026, 1, 1)), Decimal)


@pytest.mark.parametrize("espaco", list(EspacoFiscal))
def test_isenta_e_zero(tabela, espaco):
    assert tabela.taxa(espaco, Escalao.ISENTA, date(2026, 1, 1)) == 0


def test_espaco_como_texto(tabela):
    # LinhaIVA.espaco_fiscal pode chegar como texto; "PT-AC" é igual a EspacoFiscal.PT_AC
    assert tabela.taxa("PT-AC", Escalao.NORMAL, date(2026, 1, 1)) == 16


def test_todos_os_espacos_fiscais_estao_na_tabela(tabela):
    assert set(tabela.periodos) == set(EspacoFiscal)


# --- Sem taxa aplicável ----------------------------------------------------------------


@pytest.mark.parametrize("escalao", [Escalao.NORMAL, Escalao.ISENTA])
def test_espaco_desconhecido(tabela, escalao):
    # Também na isenta: um espaço sem taxas dá sempre erro, mesmo quando a taxa seria 0
    with pytest.raises(SemTaxaIVA, match="'ES'"):
        tabela.taxa("ES", escalao, date(2026, 1, 1))


def test_data_antes_do_primeiro_periodo(tabela):
    with pytest.raises(SemTaxaIVA, match="2019-12-30.*2019-12-31"):
        tabela.taxa(EspacoFiscal.PT, Escalao.NORMAL, date(2019, 12, 30))


def test_sem_taxa_e_um_lookup_error():
    assert issubclass(SemTaxaIVA, LookupError)


# --- Tabelas mal escritas são recusadas ao carregar ------------------------------------


def test_tabela_pequena():
    tabela = TabelaIVA(periodos={"PT": [periodo(date(2020, 1, 1))]})
    assert tabela.taxa("PT", Escalao.NORMAL, date(2026, 1, 1)) == 23


def test_periodos_fora_de_ordem():
    with pytest.raises(ValidationError, match="fora de ordem"):
        TabelaIVA(periodos={"PT": [periodo(date(2021, 1, 1)), periodo(date(2020, 1, 1))]})


def test_data_repetida():
    with pytest.raises(ValidationError, match="fora de ordem"):
        TabelaIVA(periodos={"PT": [periodo(date(2020, 1, 1)), periodo(date(2020, 1, 1))]})


def test_espaco_sem_periodos():
    with pytest.raises(ValidationError, match="sem períodos"):
        TabelaIVA(periodos={"PT": []})


def test_espaco_que_nao_existe():
    with pytest.raises(ValidationError):
        TabelaIVA(periodos={"ES": [periodo(date(2020, 1, 1))]})


def test_no_do_yaml_e_recusado():
    # Em YAML, NO (o código da Noruega) é lido como False; a chave tem de ser um EspacoFiscal
    lido = yaml.safe_load("NO: []")
    assert lido == {False: []}
    with pytest.raises(ValidationError):
        TabelaIVA(periodos=lido)


def test_ate_nao_e_aceite():
    # Os períodos só têm `desde` (D-017); um `ate` escrito por engano é recusado
    with pytest.raises(ValidationError, match="ate"):
        TabelaIVA(periodos={"PT": [periodo(date(2020, 1, 1), ate=date(2020, 12, 31))]})


def test_periodo_sem_uma_taxa():
    sem_normal = {"desde": date(2020, 1, 1), "reduzida": 6, "intermedia": 13}
    with pytest.raises(ValidationError, match="normal"):
        TabelaIVA(periodos={"PT": [sem_normal]})


@pytest.mark.parametrize("valor", [-1, 100, "abc"])
def test_taxa_invalida(valor):
    with pytest.raises(ValidationError):
        TabelaIVA(periodos={"PT": [periodo(date(2020, 1, 1), normal=valor)]})
