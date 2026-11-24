"""Modelos de domínio: os dados de uma fatura e o resultado do processamento.

Os modelos garantem tipos e formatos (dinheiro em Decimal, datas em date).
Não aplicam regras fiscais: um NIF inválido ou uma soma errada não são rejeitados aqui,
geram alertas em nucleo/validacoes.py (S1.7).
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


class Modelo(BaseModel):
    """Base de todos os modelos: recusa campos desconhecidos e valida as atribuições."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# --- Enumerações ---------------------------------------------------------------------


class EspacoFiscal(StrEnum):
    """Espaços fiscais do QR da AT (campos I1, J1 e K1)."""

    PT = "PT"
    PT_AC = "PT-AC"
    PT_MA = "PT-MA"


class Escalao(StrEnum):
    """Escalões de IVA. A base isenta é uma linha com o escalão isenta."""

    ISENTA = "isenta"
    REDUZIDA = "reduzida"
    INTERMEDIA = "intermedia"
    NORMAL = "normal"


class OrigemCampo(StrEnum):
    """De onde veio o valor de cada campo."""

    QR = "qr"
    REGRA = "regra"
    LLM = "llm"
    MANUAL = "manual"


class Severidade(StrEnum):
    """Severidade de um alerta. Um alerta bloqueante impede a conferência."""

    BLOQUEANTE = "bloqueante"
    AVISO = "aviso"
    INFO = "info"


class CodigoAlerta(StrEnum):
    """Os códigos de alerta da tabela do CLAUDE.md."""

    DUPLICADO = "DUPLICADO"
    NIF_ADQUIRENTE_DIFERENTE = "NIF_ADQUIRENTE_DIFERENTE"
    POSSIVEL_DUPLICADO = "POSSIVEL_DUPLICADO"
    NIF_EMITENTE_INVALIDO = "NIF_EMITENTE_INVALIDO"
    SOMA_NAO_BATE = "SOMA_NAO_BATE"
    IVA_NAO_BATE = "IVA_NAO_BATE"
    DATA_FUTURA = "DATA_FUTURA"
    ATCUD_FORMATO = "ATCUD_FORMATO"
    TIPO_NAO_SUPORTADO = "TIPO_NAO_SUPORTADO"
    FORNECEDOR_NOVO = "FORNECEDOR_NOVO"
    FATURA_RECIBO = "FATURA_RECIBO"
    EM_FALTA_NO_EFATURA = "EM_FALTA_NO_EFATURA"
    VALOR_ANORMAL = "VALOR_ANORMAL"


class EstadoFatura(StrEnum):
    """Estados de uma fatura (CLAUDE.md, secção Estados)."""

    A_PROCESSAR = "a_processar"
    POR_CONFERIR = "por_conferir"
    CONFERIDA = "conferida"
    EXPORTADA = "exportada"
    PAGAMENTO_APROVADO = "pagamento_aprovado"
    PAGAMENTO_RECUSADO = "pagamento_recusado"
    ERRO_LEITURA = "erro_leitura"
    DESCARTADA = "descartada"


class Finalidade(StrEnum):
    """Para que serviu uma chamada ao modelo."""

    EXTRACAO = "extracao"
    CLASSIFICACAO = "classificacao"


# --- Tipos com conversão -------------------------------------------------------------


def _converter_aaaammdd(valor: Any) -> Any:
    """Converte 'AAAAMMDD' (formato do QR) em date; o resto segue para o Pydantic.

    Sem isto, o Pydantic leria '20191231' como um timestamp Unix e daria erro.
    """
    if isinstance(valor, str) and len(valor) == 8 and valor.isdigit():
        return datetime.strptime(valor, "%Y%m%d").date()
    return valor


def _normalizar_espaco_fiscal(valor: Any) -> Any:
    """'pt-ac' passa a EspacoFiscal.PT_AC; outros países ficam como texto ('ES')."""
    if isinstance(valor, str):
        # Remove espaços e uniformiza maiúsculas
        valor = valor.strip().upper()
        try:
            return EspacoFiscal(valor)
        except ValueError:
            # Não é PT, PT-AC nem PT-MA: fica o texto (ex.: 'ES')
            return valor
    # Não é texto (ex.: None): o Pydantic decide
    return valor


Data = Annotated[date, BeforeValidator(_converter_aaaammdd)]
EspacoOuPais = Annotated[EspacoFiscal | str, BeforeValidator(_normalizar_espaco_fiscal)]

# --- Modelos -------------------------------------------------------------------------


class LinhaIVA(Modelo):
    """Base e IVA de um escalão num espaço fiscal.

    A base isenta é uma linha com escalão `isenta` e IVA 0.
    `taxa` em percentagem (16 = 16 %). É opcional porque o QR traz a base e o IVA,
    mas não a taxa: a taxa vem de config/iva.yaml (S1.6).
    """

    espaco_fiscal: EspacoOuPais
    escalao: Escalao
    taxa: Decimal | None = None
    base: Decimal
    iva: Decimal


class DadosFatura(Modelo):
    """Os campos de uma fatura. Todos opcionais, porque uma leitura pode ser parcial."""

    tipo_documento: str | None = None
    nif_emitente: str | None = None
    fornecedor_nome: str | None = None
    nif_adquirente: str | None = None
    pais_adquirente: str | None = None
    numero_documento: str | None = None
    data_documento: Data | None = None
    atcud: str | None = None
    linhas_iva: list[LinhaIVA] = Field(default_factory=list)
    nao_sujeito: Decimal | None = None
    imposto_selo: Decimal | None = None
    total_impostos: Decimal | None = None
    total: Decimal | None = None
    retencao: Decimal | None = None
    centro_custo: str | None = None
    origem_campos: dict[str, OrigemCampo] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _origem_so_de_campos_existentes(self) -> Self:

        # Campos em origem_campos que não existem em DadosFatura
        desconhecidos = set(self.origem_campos) - set(DadosFatura.model_fields)
        if desconhecidos:
            raise ValueError(f"origem_campos com campos que não existem: {sorted(desconhecidos)}")
        return self


class Alerta(Modelo):
    """Um problema detetado numa fatura. Os alertas não são estados (D-003)."""

    codigo: CodigoAlerta
    severidade: Severidade
    mensagem: str


class RegistoChamadaLLM(Modelo):
    """Uma chamada ao modelo, para custos e auditoria (tabela chamadas_modelo, S2.1)."""

    finalidade: Finalidade
    modelo: str
    prompt_versao: str
    tokens_entrada: int
    tokens_saida: int
    custo_usd: Decimal
    latencia_ms: int
    tentativas: int
    sucesso: bool
    erro: str | None = None


class ResultadoProcessamento(Modelo):
    """O que o núcleo devolve para cada fatura: dados, alertas e chamadas ao modelo."""

    dados: DadosFatura = Field(default_factory=DadosFatura)
    alertas: list[Alerta] = Field(default_factory=list)
    qr_bruto: str | None = None
    chamadas_llm: list[RegistoChamadaLLM] = Field(default_factory=list)
    erro: str | None = None
