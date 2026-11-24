"""Validação do NIF português (algoritmo em docs/REGRAS_AT.md, secção 3)."""

import random
import re

_PESOS = (9, 8, 7, 6, 5, 4, 3, 2)
_NOVE_DIGITOS = re.compile(r"[0-9]{9}")
_PREFIXO_VALIDO = re.compile(r"[0-9]{1,8}")


def normalizar_nif(texto: str) -> str:
    """Tira os espaços e o prefixo de país: 'PT 123 456 789' passa a '123456789'.

    Só limpa, não valida: um texto que não é um NIF continua a não o ser.
    """
    # split() sem argumentos parte em qualquer espaço, incluindo o não separável dos PDF
    limpo = "".join(texto.split()).upper()
    return limpo.removeprefix("PT")


def _digito_controlo(oito_digitos: str) -> int:
    """Dígito de controlo (módulo 11) a partir dos 8 primeiros dígitos."""
    soma = sum(int(d) * p for d, p in zip(oito_digitos, _PESOS, strict=True))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def nif_valido(nif: str) -> bool:
    """True se, depois de limpo, tem 9 dígitos e o dígito de controlo certo."""
    nif = normalizar_nif(nif)
    # [0-9] e não \d nem isdigit(): esses aceitam dígitos de outros alfabetos ('١', '９')
    if not _NOVE_DIGITOS.fullmatch(nif):
        return False
    return int(nif[8]) == _digito_controlo(nif[:8])


def gerar_nif_valido(prefixo: str, rng: random.Random) -> str:
    """Gera um NIF válido que começa por `prefixo` (para as faturas sintéticas, S1.8).

    O `rng` vem de fora para que a mesma semente dê sempre os mesmos NIF.
    """
    if not _PREFIXO_VALIDO.fullmatch(prefixo):
        raise ValueError(f"O prefixo tem de ter 1 a 8 dígitos: {prefixo!r}")
    aleatorios = "".join(str(rng.randrange(10)) for _ in range(8 - len(prefixo)))
    # oito dígitos, sem o dígito de controlo
    oito = prefixo + aleatorios
    return oito + str(_digito_controlo(oito))
