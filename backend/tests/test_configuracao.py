"""Testes da localização e leitura da configuração (S1.6)."""

from datetime import date

from agente_faturas.configuracao import RAIZ_REPOSITORIO, carregar_tabela_iva, pasta_config
from agente_faturas.nucleo.modelos import Escalao


def test_raiz_do_repositorio():
    assert (RAIZ_REPOSITORIO / "backend" / "pyproject.toml").is_file()
    assert (RAIZ_REPOSITORIO / "config" / "iva.yaml").is_file()


def test_relativo_conta_a_partir_da_raiz():
    assert pasta_config("config") == RAIZ_REPOSITORIO / "config"
    assert pasta_config("config/empresa_real") == RAIZ_REPOSITORIO / "config" / "empresa_real"


def test_absoluto_fica_igual(tmp_path):
    assert pasta_config(str(tmp_path)) == tmp_path


def test_nao_depende_da_pasta_onde_o_comando_corre(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert pasta_config("config") == RAIZ_REPOSITORIO / "config"


def test_usa_a_variavel_de_ambiente(monkeypatch):
    monkeypatch.setenv("CONFIG_DIR", "config/empresa_real")
    assert pasta_config() == RAIZ_REPOSITORIO / "config" / "empresa_real"


def test_sem_variavel_ou_vazia_usa_config(monkeypatch):
    monkeypatch.delenv("CONFIG_DIR", raising=False)
    assert pasta_config() == RAIZ_REPOSITORIO / "config"
    monkeypatch.setenv("CONFIG_DIR", "")
    assert pasta_config() == RAIZ_REPOSITORIO / "config"


def test_carregar_tabela_iva_de_outra_pasta(tmp_path):
    (tmp_path / "iva.yaml").write_text(
        "PT:\n  - desde: 2020-01-01\n    reduzida: 5\n    intermedia: 12\n    normal: 21\n",
        encoding="utf-8",
    )
    tabela = carregar_tabela_iva(tmp_path)
    assert tabela.taxa("PT", Escalao.NORMAL, date(2026, 1, 1)) == 21
