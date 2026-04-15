"""
Sanitização e validação de entradas do usuário.
Previne SQL injection, path traversal e outros ataques.
"""

import re
import os
from pathlib import Path


def sanitizar_nome_arquivo(nome: str) -> str:
    """
    Remove caracteres perigosos de nomes de arquivo.
    Previne path traversal (ex: ../../etc/passwd).
    """
    # remove path separators e chars perigosos
    nome = os.path.basename(nome)
    nome = re.sub(r"[^\w\s\-\.]", "_", nome)
    nome = nome.strip(". ")
    return nome or "arquivo"


def validar_extensao_excel(nome_arquivo: str) -> bool:
    """Aceita apenas .xlsx e .xls."""
    return Path(nome_arquivo).suffix.lower() in (".xlsx", ".xls")


def sanitizar_texto(texto: str, max_len: int = 200) -> str:
    """
    Limpa texto de entrada removendo chars de controle.
    Não use isso para queries SQL — use queries parametrizadas.
    """
    if not texto:
        return ""
    # remove chars de controle exceto newline e tab
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", texto)
    return texto[:max_len].strip()


def validar_inteiro(valor, minimo: int = 1, maximo: int = 9_999_999) -> int | None:
    """Valida e converte um valor para inteiro dentro de um range."""
    try:
        v = int(valor)
        if minimo <= v <= maximo:
            return v
    except (TypeError, ValueError):
        pass
    return None


def caminho_seguro(pasta_base: str, nome_arquivo: str) -> str | None:
    """
    Garante que o arquivo final está dentro da pasta esperada.
    Previne path traversal.
    """
    base = os.path.realpath(pasta_base)
    destino = os.path.realpath(os.path.join(base, sanitizar_nome_arquivo(nome_arquivo)))

    if not destino.startswith(base + os.sep) and destino != base:
        return None  # tentativa de path traversal

    return destino
