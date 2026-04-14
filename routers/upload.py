import os
import json
import shutil
from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from config import PASTA_ENTRADA
from engine.conexao import get_conexao

router = APIRouter()
templates = Jinja2Templates(directory="templates")
PASTA_TEMP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
os.makedirs(PASTA_TEMP, exist_ok=True)


def _buscar_varejistas():
    conn = get_conexao()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT cod_varejista, nome_varejista FROM varejista ORDER BY nome_varejista"
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def salvar_pendencias(cod_varejista: int, pendencias: list):
    """Salva pendências do último processamento em arquivo temp."""
    caminho = os.path.join(PASTA_TEMP, f"pendencias_{cod_varejista}.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(pendencias, f, ensure_ascii=False)


def carregar_pendencias(cod_varejista: int) -> list:
    """Carrega pendências do último processamento."""
    caminho = os.path.join(PASTA_TEMP, f"pendencias_{cod_varejista}.json")
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/", response_class=HTMLResponse)
async def pagina_upload(request: Request):
    varejistas = _buscar_varejistas()
    return templates.TemplateResponse(
        request=request, name="upload.html", context={"varejistas": varejistas}
    )


@router.post("/upload", response_class=HTMLResponse)
async def fazer_upload(
    request: Request,
    arquivo: UploadFile = File(...),
    cod_varejista: int = Form(...),
    nome_varejista: str = Form(...),
):
    nome_arquivo = f"{nome_varejista}_{arquivo.filename}"
    caminho_local = os.path.join(PASTA_ENTRADA, nome_arquivo)

    with open(caminho_local, "wb") as f:
        shutil.copyfileobj(arquivo.file, f)

    from engine.processador import processar_base

    resultado = processar_base(caminho_local, cod_varejista, nome_varejista)

    # salva pendências para a tela de validação
    if resultado.get("ok") and resultado.get("pendencias"):
        salvar_pendencias(cod_varejista, resultado["pendencias"])

    return templates.TemplateResponse(
        request=request,
        name="resultado.html",
        context={
            "resultado": resultado,
            "nome_varejista": nome_varejista,
            "cod_varejista": cod_varejista,
        },
    )
