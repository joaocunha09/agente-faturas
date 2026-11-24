"""Testes dos modelos de domínio (S1.3)."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from agente_faturas.nucleo.modelos import (
    Alerta,
    CodigoAlerta,
    DadosFatura,
    Escalao,
    EspacoFiscal,
    EstadoFatura,
    Finalidade,
    LinhaIVA,
    OrigemCampo,
    ResultadoProcessamento,
    Severidade,
)

# --- Dinheiro em Decimal ---------------------------------------------------------------


def test_total_em_texto_passa_a_decimal():
    dados = DadosFatura(total="12000.00")
    assert dados.total == Decimal("12000.00")
    assert isinstance(dados.total, Decimal)


def test_base_e_iva_em_texto_passam_a_decimal():
    linha = LinhaIVA(espaco_fiscal="PT", escalao="normal", base="80000.00", iva="18400.00")
    assert linha.base == Decimal("80000.00")
    assert linha.iva == Decimal("18400.00")


def test_decimal_soma_sem_erros_de_centimos():
    # Com float, 0.1 + 0.2 daria 0.30000000000000004 (D-004)
    a = DadosFatura(total="0.10").total
    b = DadosFatura(total="0.20").total
    assert a + b == Decimal("0.30")


@pytest.mark.parametrize("valor", ["abc", "12 000,00", ""])
def test_dinheiro_ilegivel_e_rejeitado(valor):
    with pytest.raises(ValidationError):
        DadosFatura(total=valor)


# --- Datas -----------------------------------------------------------------------------


@pytest.mark.parametrize("texto", ["20191231", "2019-12-31"])
def test_data_aaaammdd_e_iso_passam_a_date(texto):
    assert DadosFatura(data_documento=texto).data_documento == date(2019, 12, 31)


@pytest.mark.parametrize("texto", ["20191331", "2019-02-30", "31/12/2019", "ontem"])
def test_data_invalida_e_rejeitada(texto):
    with pytest.raises(ValidationError):
        DadosFatura(data_documento=texto)


# --- Espaço fiscal ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto, esperado",
    [("PT-AC", EspacoFiscal.PT_AC), ("pt-ma", EspacoFiscal.PT_MA), (" PT ", EspacoFiscal.PT)],
)
def test_espaco_fiscal_conhecido_passa_a_enum(texto, esperado):
    linha = LinhaIVA(espaco_fiscal=texto, escalao="normal", base="1", iva="0.23")
    assert linha.espaco_fiscal is esperado


def test_espacos_fiscais_usam_os_codigos_do_qr():
    assert {e.value for e in EspacoFiscal} == {"PT", "PT-AC", "PT-MA"}


def test_espaco_fiscal_de_outro_pais_fica_como_texto():
    linha = LinhaIVA(espaco_fiscal="ES", escalao="normal", base="1", iva="0.21")
    assert linha.espaco_fiscal == "ES"
    assert not isinstance(linha.espaco_fiscal, EspacoFiscal)


def test_escaloes_sao_os_do_plano():
    assert {e.value for e in Escalao} == {"isenta", "reduzida", "intermedia", "normal"}


def test_base_isenta_e_uma_linha_com_iva_zero():
    linha = LinhaIVA(espaco_fiscal="PT", escalao="isenta", base="12000.00", iva="0")
    assert linha.escalao is Escalao.ISENTA
    assert linha.iva == 0
    assert linha.taxa is None


# --- DadosFatura -----------------------------------------------------------------------


def test_dados_fatura_vazios_sao_validos():
    dados = DadosFatura()
    assert dados.total is None
    assert dados.linhas_iva == []
    assert dados.origem_campos == {}


def test_campo_desconhecido_e_rejeitado():
    with pytest.raises(ValidationError):
        DadosFatura(totl="10.00")


def test_atribuicao_tambem_e_convertida():
    dados = DadosFatura()
    dados.total = "5.00"
    assert dados.total == Decimal("5.00")


def test_origem_campos_aceita_campos_existentes():
    dados = DadosFatura(total="1.00", origem_campos={"total": "qr"})
    assert dados.origem_campos["total"] is OrigemCampo.QR


def test_origem_campos_rejeita_campos_que_nao_existem():
    with pytest.raises(ValidationError):
        DadosFatura(origem_campos={"totl": "qr"})


# --- Alertas, estados e resultado ------------------------------------------------------


def test_alerta_com_codigo_desconhecido_e_rejeitado():
    with pytest.raises(ValidationError):
        Alerta(codigo="NIF_ERRADO", severidade="aviso", mensagem="...")


def test_alerta_valido():
    alerta = Alerta(codigo="DUPLICADO", severidade="bloqueante", mensagem="Já existe")
    assert alerta.codigo is CodigoAlerta.DUPLICADO
    assert alerta.severidade is Severidade.BLOQUEANTE


def test_estados_sao_os_do_claude_md():
    assert {e.value for e in EstadoFatura} == {
        "a_processar",
        "por_conferir",
        "conferida",
        "exportada",
        "pagamento_aprovado",
        "pagamento_recusado",
        "erro_leitura",
        "descartada",
    }


def test_finalidades_sao_as_da_tabela_chamadas_modelo():
    assert {f.value for f in Finalidade} == {"extracao", "classificacao"}


def test_resultado_vazio_tem_valores_por_defeito():
    resultado = ResultadoProcessamento()
    assert resultado.dados == DadosFatura()
    assert resultado.alertas == []
    assert resultado.chamadas_llm == []
    assert resultado.qr_bruto is None
    assert resultado.erro is None
