"""
Gerenciamento seguro de credenciais.
As credenciais do banco são armazenadas criptografadas em vez de texto puro.
"""

import os
import base64
import json
from pathlib import Path
from cryptography.fernet import Fernet


CONFIG_PATH = Path.home() / ".mavi_bases" / "config.enc"


def _get_ou_criar_chave() -> bytes:
    """
    Chave derivada do nome da máquina + usuário Windows.
    Única por máquina — não funciona em outra máquina.
    """
    import hashlib
    import platform

    identificador = f"{platform.node()}-{os.getlogin()}-mavi2025"
    chave_raw = hashlib.sha256(identificador.encode()).digest()
    return base64.urlsafe_b64encode(chave_raw)


def _fernet() -> Fernet:
    return Fernet(_get_ou_criar_chave())


def salvar_credenciais(host: str, port: int, user: str, password: str):
    """Salva credenciais criptografadas no diretório home do usuário."""
    dados = json.dumps(
        {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
        }
    ).encode()

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    encrypted = _fernet().encrypt(dados)
    CONFIG_PATH.write_bytes(encrypted)


def carregar_credenciais() -> dict | None:
    """Carrega e descriptografa as credenciais salvas."""
    if not CONFIG_PATH.exists():
        return None
    try:
        encrypted = CONFIG_PATH.read_bytes()
        dados = _fernet().decrypt(encrypted)
        return json.loads(dados.decode())
    except Exception:
        return None


def credenciais_existem() -> bool:
    return CONFIG_PATH.exists()


def apagar_credenciais():
    """Remove as credenciais salvas (logout total)."""
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
