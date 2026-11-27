"""Onde está a configuração e como se lê (CONFIG_DIR, D-015).

Fica fora do núcleo: quem chama o núcleo lê os ficheiros e passa-lhe o resultado (D-016).
"""

import os
from pathlib import Path
from typing import Any

import yaml

from agente_faturas.nucleo.iva import TabelaIVA

# configuracao.py → agente_faturas → src → backend → raiz do repositório
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]


def pasta_config(valor: str | None = None) -> Path:
    """A pasta dos YAML. Um caminho relativo conta a partir da raiz do repositório.

    Sem `valor`, usa a variável de ambiente CONFIG_DIR; vazia ou em falta, usa `config`.
    """
    if valor is None:
        valor = os.environ.get("CONFIG_DIR", "")
    caminho = Path(valor.strip() or "config")
    return caminho if caminho.is_absolute() else RAIZ_REPOSITORIO / caminho


def carregar_tabela_iva(pasta: Path | None = None) -> TabelaIVA:
    """Lê e valida iva.yaml. Sem `pasta`, usa pasta_config()."""
    pasta = pasta if pasta is not None else pasta_config()
    return TabelaIVA(periodos=_ler_yaml(pasta / "iva.yaml"))


def _ler_yaml(caminho: Path) -> Any:
    with caminho.open(encoding="utf-8") as ficheiro:
        # safe_load só cria dicionários, listas, textos, números e datas; nunca objetos Python
        return yaml.safe_load(ficheiro)
