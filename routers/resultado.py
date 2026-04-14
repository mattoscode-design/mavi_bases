import os
from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from config import PASTA_SAIDA

router = APIRouter(prefix="/resultado")


@router.get("/download/{nome_arquivo}")
async def download_arquivo(nome_arquivo: str):
    """Download do Excel tratado."""
    caminho = os.path.join(PASTA_SAIDA, nome_arquivo)
    if not os.path.exists(caminho):
        return JSONResponse({"erro": "Arquivo não encontrado."}, status_code=404)
    return FileResponse(
        path=caminho,
        filename=nome_arquivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.get("/historico")
async def listar_historico():
    """Lista todos os arquivos gerados na pasta saidas."""
    arquivos = []
    for f in os.listdir(PASTA_SAIDA):
        if f.endswith(".xlsx"):
            caminho = os.path.join(PASTA_SAIDA, f)
            arquivos.append({
                "nome":     f,
                "tamanho":  os.path.getsize(caminho),
                "criado_em": os.path.getmtime(caminho),
            })
    arquivos.sort(key=lambda x: x["criado_em"], reverse=True)
    return arquivos
