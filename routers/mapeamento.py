import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
from engine.conexao import get_conexao
from config import PASTA_ENTRADA

router = APIRouter(prefix="/mapeamento")
templates = Jinja2Templates(directory="templates")


def carregar_mapeamento_banco(cod_varejista: int) -> list:
    conn = get_conexao()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT coluna_entrada, coluna_saida, tipo_acao
        FROM mapeamento_colunas
        WHERE cod_varejista = %s
        ORDER BY ordem
        """,
        (cod_varejista,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def salvar_mapeamento_banco(cod_varejista: int, colunas: list):
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM mapeamento_colunas WHERE cod_varejista = %s", (cod_varejista,)
    )
    for ordem, col in enumerate(colunas):
        cursor.execute(
            """
            INSERT INTO mapeamento_colunas
                (cod_varejista, coluna_entrada, coluna_saida, tipo_acao, formula, ordem)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                cod_varejista,
                col.get("coluna_entrada"),
                col.get("coluna_saida", ""),
                col.get("tipo_acao", "manter"),
                col.get("formula", ""),
                ordem,
            ),
        )
    conn.commit()
    cursor.close()
    conn.close()


@router.get("/configurar", response_class=HTMLResponse)
async def pagina_configurar(request: Request):
    conn = get_conexao()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT cod_varejista, nome_varejista FROM varejista ORDER BY nome_varejista"
    )
    varejistas = cursor.fetchall()
    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="mapeamento_upload.html",
        context={"varejistas": varejistas},
    )


@router.post("/ler-colunas", response_class=HTMLResponse)
async def ler_colunas(
    request: Request,
    arquivo: UploadFile = File(...),
    cod_varejista: int = Form(...),
):
    nome_temp = f"temp_{cod_varejista}_{arquivo.filename}"
    caminho = os.path.join(PASTA_ENTRADA, nome_temp)
    with open(caminho, "wb") as f:
        shutil.copyfileobj(arquivo.file, f)

    try:
        df = pd.read_excel(caminho, nrows=3, dtype=str)
        colunas = list(df.columns.str.strip())
        amostra = df.head(3).fillna("").values.tolist()
    except Exception as e:
        return JSONResponse({"ok": False, "erro": str(e)})

    mapeamento_salvo = {
        m["coluna_entrada"]: m
        for m in carregar_mapeamento_banco(cod_varejista)
        if m["coluna_entrada"]
    }

    conn = get_conexao()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT nome_varejista FROM varejista WHERE cod_varejista = %s",
        (cod_varejista,),
    )
    row = cursor.fetchone()
    nome_varejista = row["nome_varejista"] if row else ""
    cursor.close()
    conn.close()

    tipos_acao = [
        ("id_loja", "🏪 É o ID da loja"),
        ("renomear", "✏️ Renomear coluna"),
        ("cruzar_ean", "🔍 Cruzar EAN com banco"),
        ("separar_mes_ano", "📅 Separar MÊS e ANO"),
        ("calcular_quantidade", "🧮 Calcular QUANTIDADE"),
        ("manter", "✅ Manter como está"),
        ("ignorar", "❌ Ignorar coluna"),
    ]

    return templates.TemplateResponse(
        request=request,
        name="mapeamento_colunas.html",
        context={
            "colunas": colunas,
            "amostra": amostra,
            "cod_varejista": cod_varejista,
            "nome_varejista": nome_varejista,
            "nome_arquivo": nome_temp,
            "mapeamento_salvo": mapeamento_salvo,
            "tipos_acao": tipos_acao,
        },
    )


@router.post("/salvar")
async def salvar_configuracao(request: Request):
    dados = await request.json()
    cod_varejista = dados.get("cod_varejista")
    colunas = dados.get("colunas", [])

    if not cod_varejista or not colunas:
        return JSONResponse({"ok": False, "erro": "Dados incompletos."})

    try:
        salvar_mapeamento_banco(cod_varejista, colunas)
        return JSONResponse({"ok": True, "mensagem": "Configuração salva com sucesso!"})
    except Exception as e:
        return JSONResponse({"ok": False, "erro": str(e)}, status_code=500)
