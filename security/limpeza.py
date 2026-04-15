"""
Limpeza segura de arquivos temporários.
Arquivos com dados de clientes são deletados após processamento.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta


def deletar_arquivo_seguro(caminho: str):
    """
    Deleta um arquivo de forma segura.
    Sobrescreve o conteúdo antes de deletar para dificultar recuperação.
    """
    try:
        path = Path(caminho)
        if not path.exists():
            return

        # sobrescreve com zeros antes de deletar
        tamanho = path.stat().st_size
        with open(path, "wb") as f:
            f.write(b"\x00" * min(tamanho, 1024 * 1024))  # max 1MB de zeros

        path.unlink()
    except Exception:
        # se falhar, tenta deletar direto
        try:
            os.remove(caminho)
        except Exception:
            pass


def limpar_entradas_antigas(pasta_entrada: str, horas: int = 24):
    """
    Remove bases Excel da pasta entradas/ após X horas.
    Dados de clientes não devem ficar em disco por muito tempo.
    """
    limite = datetime.now() - timedelta(hours=horas)
    pasta = Path(pasta_entrada)

    if not pasta.exists():
        return

    removidos = 0
    for arquivo in pasta.glob("*.xls*"):
        try:
            mtime = datetime.fromtimestamp(arquivo.stat().st_mtime)
            if mtime < limite:
                deletar_arquivo_seguro(str(arquivo))
                removidos += 1
        except Exception:
            continue

    return removidos


def limpar_temp(pasta_temp: str):
    """Remove arquivos temporários de pendências."""
    try:
        shutil.rmtree(pasta_temp, ignore_errors=True)
        os.makedirs(pasta_temp, exist_ok=True)
    except Exception:
        pass


def limpar_saidas_antigas(pasta_saida: str, dias: int = 30):
    """
    Remove arquivos tratados da pasta saidas/ após X dias.
    O usuário já baixou, não precisa ficar guardado.
    """
    limite = datetime.now() - timedelta(days=dias)
    pasta = Path(pasta_saida)

    if not pasta.exists():
        return

    for arquivo in pasta.glob("*.xlsx"):
        try:
            mtime = datetime.fromtimestamp(arquivo.stat().st_mtime)
            if mtime < limite:
                arquivo.unlink()
        except Exception:
            continue
