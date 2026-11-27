"""Taxas de IVA por espaço fiscal, escalão e data (docs/REGRAS_AT.md, secção 4).

A tabela vem de config/iva.yaml e é lida em agente_faturas/configuracao.py.
Este módulo só a valida e a consulta; não lê ficheiros (núcleo puro, D-002 e D-016).
"""

from datetime import date
from decimal import Decimal
from itertools import pairwise
from typing import Annotated, Self

from pydantic import Field, model_validator

from agente_faturas.nucleo.modelos import Escalao, EspacoFiscal, Modelo

# Uma taxa em percentagem (16 = 16 %)
Taxa = Annotated[Decimal, Field(ge=0, lt=100)]  # 0 <= Taxa < 100


class SemTaxaIVA(LookupError):
    """Não há taxa para este espaço fiscal nesta data."""


class PeriodoIVA(Modelo):
    """Taxas em vigor desde `desde` até ao dia anterior ao período seguinte (D-017)."""

    desde: date
    reduzida: Taxa
    intermedia: Taxa
    normal: Taxa


class TabelaIVA(Modelo):
    """Os períodos de cada espaço fiscal, do mais antigo para o mais recente."""

    periodos: dict[EspacoFiscal, list[PeriodoIVA]]

    @model_validator(mode="after")
    def _periodos_por_ordem(self) -> Self:
        for espaco, periodos in self.periodos.items():
            if not periodos:
                raise ValueError(f"{espaco}: sem períodos")
            # Datas estritamente crescentes: apanha períodos trocados e datas repetidas
            datas = [periodo.desde for periodo in periodos]
            if any(anterior >= seguinte for anterior, seguinte in pairwise(datas)):
                raise ValueError(f"{espaco}: períodos fora de ordem ou com datas repetidas")
        return self

    def taxa(self, espaco: EspacoFiscal | str, escalao: Escalao, data: date) -> Decimal:
        """A taxa (%) do escalão no espaço fiscal, na data do documento.

        Lança SemTaxaIVA se o espaço fiscal não estiver na tabela (por exemplo, 'ES')
        ou se a data for anterior ao primeiro período.
        """
        periodo = self._periodo(espaco, data)
        taxas = {
            Escalao.ISENTA: Decimal("0"),
            Escalao.REDUZIDA: periodo.reduzida,
            Escalao.INTERMEDIA: periodo.intermedia,
            Escalao.NORMAL: periodo.normal,
        }
        return taxas[escalao]

    def _periodo(self, espaco: EspacoFiscal | str, data: date) -> PeriodoIVA:
        periodos = self.periodos.get(espaco)
        if periodos is None:
            raise SemTaxaIVA(f"Espaço fiscal sem taxas de IVA: '{espaco}'")
        # Do mais recente para o mais antigo: o primeiro que já tinha começado nessa data
        for periodo in reversed(periodos):
            if periodo.desde <= data:
                return periodo
        raise SemTaxaIVA(
            f"{espaco}: sem taxas de IVA para {data.isoformat()}; "
            f"o primeiro período começa em {periodos[0].desde.isoformat()}"
        )
