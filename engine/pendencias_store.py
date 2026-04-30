"""
Persistência de pendências por banco de dados.
Salva em ~/.mavi_bases/pendencias/<banco>.json para sobreviver a reinicializações.
"""

import json
from pathlib import Path
from engine.logger import get_logger

_log = get_logger("pendencias_store")
_BASE_DIR = Path.home() / ".mavi_bases" / "pendencias"


def _caminho(banco: str) -> Path:
    _BASE_DIR.mkdir(parents=True, exist_ok=True)
    nome = banco.replace("/", "_").replace("\\", "_").replace("..", "_")
    return _BASE_DIR / f"{nome}.json"


def carregar(banco: str) -> list:
    """Carrega pendências salvas para o banco dado."""
    try:
        path = _caminho(banco)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        _log.warning("Não foi possível carregar pendências de '%s': %s", banco, e)
    return []


def salvar(banco: str, pendencias: list) -> None:
    """Salva/atualiza a lista de pendências para o banco dado."""
    try:
        path = _caminho(banco)
        path.write_text(
            json.dumps(pendencias, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        _log.warning("Não foi possível salvar pendências para '%s': %s", banco, e)


def mesclar(banco: str, novas: list) -> list:
    """
    Carrega pendências existentes, adiciona novas (sem duplicatas por chave),
    salva e retorna a lista completa atualizada.
    """
    existentes = carregar(banco)
    vistas = {p.get("chave") for p in existentes}
    adicionadas = [p for p in novas if p.get("chave") not in vistas]
    total = existentes + adicionadas
    salvar(banco, total)
    return total


def limpar(banco: str) -> None:
    """Remove todas as pendências salvas para o banco dado."""
    try:
        path = _caminho(banco)
        if path.exists():
            path.unlink()
    except Exception as e:
        _log.warning("Não foi possível limpar pendências de '%s': %s", banco, e)
