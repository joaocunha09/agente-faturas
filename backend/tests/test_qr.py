"""Testes do parser do QR code (S1.5)."""

from datetime import date
from decimal import Decimal

import pytest

from agente_faturas.nucleo.modelos import Escalao, EspacoFiscal, OrigemCampo
from agente_faturas.nucleo.qr import QRInvalido, interpretar_qr, parece_qr_fatura

# Exemplo 1 da especificação técnica da AT (docs/REGRAS_AT.md, secção 1)
EXEMPLO_AT = (
    "A:123456789*B:999999990*C:PT*D:FT*E:N*F:20191231*G:FT AB2019/0035*H:CSDF7T5H-0035"
    "*I1:PT*I2:12000.00*I3:15000.00*I4:900.00*I5:50000.00*I6:6500.00*I7:80000.00*I8:18400.00"
    "*J1:PT-AC*J2:10000.00*J3:25000.56*J4:1000.02*J5:75000.00*J6:6750.00*J7:100000.00"
    "*J8:18000.00*K1:PT-MA*K2:5000.00*K3:12500.00*K4:625.00*K5:25000.00*K6:3000.00"
    "*K7:40000.00*K8:8800.00*L:100.00*M:25.00*N:64000.02*O:513600.58*P:100.00*Q:kLp0*R:9999"
    "*S:TB;PT00000000000000000000000;513500.58"
)

# Uma fatura simples, só com o grupo I, para os testes de casos particulares
SIMPLES = (
    "A:123456789*B:999999990*C:PT*D:FS*E:N*F:20260115*G:FS A/12*H:ABCD1234-12"
    "*I1:PT-AC*I7:100.00*I8:16.00*N:16.00*O:116.00*Q:ab12*R:1234"
)


def sem_campo(texto: str, codigo: str) -> str:
    """O mesmo QR sem o campo `codigo`."""
    return "*".join(p for p in texto.split("*") if not p.startswith(f"{codigo}:"))


# --- Exemplo oficial da AT -------------------------------------------------------------


def test_exemplo_at_campos_principais():
    dados = interpretar_qr(EXEMPLO_AT)
    assert dados.nif_emitente == "123456789"
    assert dados.nif_adquirente == "999999990"
    assert dados.pais_adquirente == "PT"
    assert dados.tipo_documento == "FT"
    assert dados.numero_documento == "FT AB2019/0035"
    assert dados.atcud == "CSDF7T5H-0035"
    assert dados.data_documento == date(2019, 12, 31)


def test_exemplo_at_totais():
    dados = interpretar_qr(EXEMPLO_AT)
    assert dados.total_impostos == Decimal("64000.02")
    assert dados.total == Decimal("513600.58")
    assert dados.nao_sujeito == Decimal("100.00")
    assert dados.imposto_selo == Decimal("25.00")
    assert dados.retencao == Decimal("100.00")


def test_exemplo_at_tem_12_linhas_em_3_espacos_fiscais():
    linhas = interpretar_qr(EXEMPLO_AT).linhas_iva
    assert len(linhas) == 12
    assert all(linha.base > 0 for linha in linhas)
    assert {linha.espaco_fiscal for linha in linhas} == {
        EspacoFiscal.PT,
        EspacoFiscal.PT_AC,
        EspacoFiscal.PT_MA,
    }


def test_exemplo_at_linha_dos_acores_taxa_reduzida():
    linhas = interpretar_qr(EXEMPLO_AT).linhas_iva
    reduzida_ac = [
        linha
        for linha in linhas
        if linha.espaco_fiscal is EspacoFiscal.PT_AC and linha.escalao is Escalao.REDUZIDA
    ]
    assert len(reduzida_ac) == 1
    assert reduzida_ac[0].base == Decimal("25000.56")
    assert reduzida_ac[0].iva == Decimal("1000.02")


def test_exemplo_at_base_isenta_tem_iva_zero():
    linhas = interpretar_qr(EXEMPLO_AT).linhas_iva
    isentas = [linha for linha in linhas if linha.escalao is Escalao.ISENTA]
    assert [linha.base for linha in isentas] == [
        Decimal("12000.00"),
        Decimal("10000.00"),
        Decimal("5000.00"),
    ]
    assert all(linha.iva == 0 for linha in isentas)


def test_linhas_de_cada_grupo_pela_ordem_dos_escaloes():
    # A ordem tem de ser sempre a mesma: a avaliação e o ecrã de conferência dependem dela
    linhas = interpretar_qr(EXEMPLO_AT).linhas_iva
    ordem = [Escalao.ISENTA, Escalao.REDUZIDA, Escalao.INTERMEDIA, Escalao.NORMAL]
    assert [linha.escalao for linha in linhas] == ordem * 3


def test_exemplo_at_somas_batem():
    # As contas do REGRAS_AT.md: N = soma dos IVA + M; O = soma das bases + L + N
    dados = interpretar_qr(EXEMPLO_AT)
    soma_iva = sum(linha.iva for linha in dados.linhas_iva)
    soma_bases = sum(linha.base for linha in dados.linhas_iva)
    assert soma_iva + dados.imposto_selo == dados.total_impostos
    assert soma_bases + dados.nao_sujeito + dados.total_impostos == dados.total


def test_tudo_o_que_veio_do_qr_tem_origem_qr():
    dados = interpretar_qr(EXEMPLO_AT)
    assert dados.origem_campos["total"] is OrigemCampo.QR
    assert dados.origem_campos["linhas_iva"] is OrigemCampo.QR
    assert "fornecedor_nome" not in dados.origem_campos  # não vem no QR
    assert "centro_custo" not in dados.origem_campos


# --- Casos particulares ----------------------------------------------------------------


def test_qr_sem_grupos_j_e_k():
    dados = interpretar_qr(SIMPLES)
    assert len(dados.linhas_iva) == 1
    linha = dados.linhas_iva[0]
    assert linha.espaco_fiscal is EspacoFiscal.PT_AC
    assert linha.escalao is Escalao.NORMAL
    assert (linha.base, linha.iva) == (Decimal("100.00"), Decimal("16.00"))
    assert dados.nao_sujeito is None
    assert dados.retencao is None


def test_i1_zero_quer_dizer_sem_iva():
    texto = (
        "A:123456789*B:999999990*C:PT*D:FT*E:N*F:20260115*G:FT A/1*H:ABCD1234-1"
        "*I1:0*L:50.00*N:0.00*O:50.00*Q:ab12*R:1234"
    )
    dados = interpretar_qr(texto)
    assert dados.linhas_iva == []
    assert dados.nao_sujeito == Decimal("50.00")


def test_campo_s_com_dois_pontos_e_ponto_e_virgula():
    dados = interpretar_qr(SIMPLES + "*S:TB;PT50000000000000000000000;IBAN:PT50")
    assert dados.total == Decimal("116.00")


def test_g_com_espacos_e_barras_fica_inteiro():
    assert interpretar_qr(SIMPLES).numero_documento == "FS A/12"


def test_espaco_fiscal_de_outro_pais():
    texto = SIMPLES.replace("I1:PT-AC", "I1:ES")
    assert interpretar_qr(texto).linhas_iva[0].espaco_fiscal == "ES"


# --- QR malformado ---------------------------------------------------------------------


@pytest.mark.parametrize("codigo", ["A", "F", "G", "H", "I1", "N", "O", "Q", "R"])
def test_falta_campo_obrigatorio(codigo):
    with pytest.raises(QRInvalido, match="Faltam campos obrigatórios"):
        interpretar_qr(sem_campo(SIMPLES, codigo))


@pytest.mark.parametrize("valor", ["abc", "12,50", "NaN", "Infinity", "1e3", "-5.00", ""])
def test_valor_monetario_invalido(valor):
    with pytest.raises(QRInvalido):
        interpretar_qr(SIMPLES.replace("O:116.00", f"O:{valor}"))


@pytest.mark.parametrize("valor", ["20261332", "20260230", "2026-01-15", "15012026x"])
def test_data_invalida(valor):
    with pytest.raises(QRInvalido, match="Campo F"):
        interpretar_qr(SIMPLES.replace("F:20260115", f"F:{valor}"))


@pytest.mark.parametrize(
    "texto, mensagem",
    [
        ("https://www.exemplo.pt/fatura/123", "sem ':'|desconhecido"),
        (SIMPLES + "*Z:1", "desconhecido"),
        (SIMPLES + "*A:987654321", "repetido"),
        (SIMPLES + "*", "sem ':'"),
        (SIMPLES.replace("*I8:16.00", ""), "juntos"),
        (SIMPLES + "*J7:10.00*J8:1.60", "sem J1"),
        (SIMPLES.replace("I1:PT-AC*I7:100.00*I8:16.00", "I1:0*I7:100.00*I8:16.00"), "I1:0"),
    ],
)
def test_qr_malformado(texto, mensagem):
    with pytest.raises(QRInvalido, match=mensagem):
        interpretar_qr(texto)


def test_qr_invalido_e_um_value_error():
    # Quem só conhece ValueError (por exemplo, o pipeline) também o apanha
    assert issubclass(QRInvalido, ValueError)


# --- parece_qr_fatura ------------------------------------------------------------------


@pytest.mark.parametrize("texto", [EXEMPLO_AT, SIMPLES, "  " + SIMPLES + "\n"])
def test_parece_qr_fatura(texto):
    assert parece_qr_fatura(texto)


@pytest.mark.parametrize(
    "texto",
    [
        "https://www.exemplo.pt/fatura/123",
        "WIFI:S:Hotel;T:WPA;P:segredo;;",
        "",
        "A:12345*B:999999990",  # NIF do emitente sem 9 dígitos
        "B:999999990*A:123456789",  # não começa por A
    ],
)
def test_nao_parece_qr_fatura(texto):
    assert not parece_qr_fatura(texto)
