"""Leitura do texto do QR code das faturas (docs/REGRAS_AT.md, secção 1).

O texto tem a forma `A:123456789*B:999999990*...`: campos separados por `*`,
cada um `Código:Valor`. Este módulo só interpreta o texto; ler o QR de uma imagem é a S2.2.
"""

import re
from datetime import date, datetime
from decimal import Decimal

from agente_faturas.nucleo.modelos import DadosFatura, Escalao, LinhaIVA, OrigemCampo

_CAMPOS_TEXTO = {
    "A": "nif_emitente",
    "B": "nif_adquirente",
    "C": "pais_adquirente",
    "D": "tipo_documento",
    "G": "numero_documento",
    "H": "atcud",
}

_CAMPOS_DINHEIRO = {
    "L": "nao_sujeito",
    "M": "imposto_selo",
    "N": "total_impostos",
    "O": "total",
    "P": "retencao",
}

# Lidos mas não guardados em DadosFatura: estado (E), hash (Q), certificado (R), outras (S).
# O texto completo fica em ResultadoProcessamento.qr_bruto.
_CAMPOS_SO_NO_QR = {"E", "Q", "R", "S"}

# Em cada grupo (I, J, K): (código da base, código do IVA, escalão). A base isenta não tem IVA.
_ESCALOES = {
    ("2", None, Escalao.ISENTA),
    ("3", "4", Escalao.REDUZIDA),
    ("5", "6", Escalao.INTERMEDIA),
    ("7", "8", Escalao.NORMAL),
}

_GRUPOS_IVA = ("I", "J", "K")

_OBRIGATORIOS = {"A", "B", "C", "D", "E", "F", "G", "H", "I1", "N", "O", "Q", "R"}
_CODIGOS_VALIDOS = (
    set(_CAMPOS_TEXTO)
    | set(_CAMPOS_DINHEIRO)
    | _CAMPOS_SO_NO_QR
    | {"F"}
    | {f"{grupo}{n}" for grupo in _GRUPOS_IVA for n in range(1, 9)}
)

_DINHEIRO = re.compile(r"[0-9]+(\.[0-9]+)?")
_DATA = re.compile(r"[0-9]{8}")
_INICIO_QR_AT = re.compile(r"A:[0-9]{9}\*B:")


class QRInvalido(ValueError):
    """O texto não é um QR de fatura válido. O pipeline passa a usar o LLM."""


def parece_qr_fatura(texto: str) -> bool:
    """True se o texto começa como um QR da AT (`A:` + 9 dígitos + `*B:`).

    Serve para escolher entre vários QR na mesma página (por exemplo, um link no rodapé).
    Não garante que o QR é válido: isso é com `interpretar_qr`.
    """
    return _INICIO_QR_AT.match(texto.strip()) is not None


def interpretar_qr(texto: str) -> DadosFatura:
    """Converte o texto do QR em DadosFatura. Lança QRInvalido se o texto não seguir a norma."""
    campos = _separar_campos(texto)

    faltam = _OBRIGATORIOS - campos.keys()
    if faltam:
        raise QRInvalido(f"Faltam campos obrigatórios: {', '.join(sorted(faltam))}")

    valores: dict = {nome: campos[codigo] for codigo, nome in _CAMPOS_TEXTO.items()}
    valores["data_documento"] = _data(campos["F"])
    for codigo, nome in _CAMPOS_DINHEIRO.items():
        if codigo in campos:
            valores[nome] = _dinheiro(codigo, campos[codigo])
    valores["linhas_iva"] = [linha for grupo in _GRUPOS_IVA for linha in _linhas(grupo, campos)]

    valores["origem_campos"] = {nome: OrigemCampo.QR for nome in valores}
    return DadosFatura(**valores)


def _separar_campos(texto: str) -> dict[str, str]:
    """'A:1*G:FT A/1' passa a {'A': '1', 'G': 'FT A/1'}."""
    campos: dict[str, str] = {}
    for parte in texto.strip().split("*"):
        # Só o primeiro ':' separa: o valor pode ter ':' (por exemplo, no campo S)
        codigo, separador, valor = parte.partition(":")
        if not separador:
            raise QRInvalido(f"Campo sem ':': {parte!r}")
        if codigo not in _CODIGOS_VALIDOS:
            raise QRInvalido(f"Código desconhecido: {codigo!r}")
        if codigo in campos:
            raise QRInvalido(f"Código repetido: {codigo!r}")
        if valor == "":
            raise QRInvalido(f"Campo {codigo} sem valor")
        campos[codigo] = valor
    return campos


def _dinheiro(codigo: str, valor: str) -> Decimal:
    # A expressão regular recusa o que Decimal aceitaria: 'NaN', 'Infinity', '1e3', '-5'
    if not _DINHEIRO.fullmatch(valor):
        raise QRInvalido(f"Campo {codigo}: valor monetário inválido {valor!r}")
    return Decimal(valor)


def _data(valor: str) -> date:
    if not _DATA.fullmatch(valor):
        raise QRInvalido(f"Campo F: data tem de ser AAAAMMDD, recebido {valor!r}")
    try:
        return datetime.strptime(valor, "%Y%m%d").date()
    except ValueError:
        raise QRInvalido(f"Campo F: data inexistente {valor!r}") from None


def _linhas(grupo: str, campos: dict[str, str]) -> list[LinhaIVA]:
    """As linhas de IVA de um grupo (I, J ou K). O espaço fiscal vem do campo 1 do grupo."""
    espaco = campos.get(f"{grupo}1")
    outros = [c for c in campos if c.startswith(grupo) and c != f"{grupo}1"]

    if espaco is None:
        if outros:
            raise QRInvalido(f"{', '.join(sorted(outros))} sem {grupo}1")
        return []
    if espaco == "0":
        # 'I1:0': documento sem IVA; não pode haver bases neste grupo
        if outros:
            raise QRInvalido(f"{grupo}1:0 mas o grupo tem valores: {', '.join(sorted(outros))}")
        return []

    linhas = []
    for cod_base, cod_iva, escalao in _ESCALOES:
        base = campos.get(f"{grupo}{cod_base}")
        iva = campos.get(f"{grupo}{cod_iva}") if cod_iva else "0"
        if base is None and (cod_iva is None or iva is None):
            continue
        if base is None or iva is None:
            raise QRInvalido(f"{grupo}{cod_base} e {grupo}{cod_iva} têm de aparecer juntos")
        linhas.append(
            LinhaIVA(
                espaco_fiscal=espaco,
                escalao=escalao,
                base=_dinheiro(f"{grupo}{cod_base}", base),
                iva=_dinheiro(f"{grupo}{cod_iva}", iva) if cod_iva else Decimal("0"),
            )
        )
    return linhas
