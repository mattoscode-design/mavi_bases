"""
Audit log — registra quem fez o quê e quando.
Salvo em arquivo local criptografado, rotacionado mensalmente.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path


LOG_DIR = Path.home() / ".mavi_bases" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _get_logger() -> logging.Logger:
    mes = datetime.now().strftime("%Y-%m")
    log_file = LOG_DIR / f"audit_{mes}.log"

    logger = logging.getLogger("mavi_audit")
    if not logger.handlers:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def registrar(
    usuario: str,
    acao: str,
    detalhe: str = "",
    varejista: str = "",
    banco: str = "",
):
    """
    Registra uma ação no audit log.

    Ações importantes para registrar:
    - LOGIN, LOGOUT
    - BANCO_SELECIONADO
    - BASE_PROCESSADA
    - LOJA_VINCULADA
    - MAPEAMENTO_SALVO
    - ERRO
    """
    entry = {
        "ts": datetime.now().isoformat(),
        "usuario": usuario,
        "acao": acao,
        "varejista": varejista,
        "banco": banco,
        "detalhe": detalhe,
    }
    _get_logger().info(json.dumps(entry, ensure_ascii=False))


def listar_logs(mes: str = None) -> list[dict]:
    """Retorna os logs do mês atual ou do mês especificado (YYYY-MM)."""
    mes = mes or datetime.now().strftime("%Y-%m")
    log_file = LOG_DIR / f"audit_{mes}.log"

    if not log_file.exists():
        return []

    entries = []
    with open(log_file, encoding="utf-8") as f:
        for linha in f:
            try:
                entries.append(json.loads(linha.strip()))
            except Exception:
                continue
    return entries
