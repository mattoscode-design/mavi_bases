from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from engine.conexao import get_conexao
from engine.matcher import vincular_loja_manualmente
from models.schemas import VincularLojaRequest
from routers.upload import carregar_pendencias

router = APIRouter(prefix="/validacao")
templates = Jinja2Templates(directory="templates")


@router.get("/lojas", response_class=HTMLResponse)
async def pagina_validacao(request: Request, cod_varejista: int):
    """Lista lojas pendentes do último processamento."""
    conn = get_conexao()
    cursor = conn.cursor(dictionary=True)

    # busca lojas do banco com nome automático se não tiver nome
    cursor.execute(
        """
        SELECT id_loja,
               COALESCE(NULLIF(TRIM(nome_loja), ''), CONCAT('Loja ', id_loja)) AS nome_loja
        FROM loja
        ORDER BY nome_loja
        """
    )
    lojas = cursor.fetchall()

    # busca nome do varejista
    cursor.execute(
        "SELECT nome_varejista FROM varejista WHERE cod_varejista = %s",
        (cod_varejista,),
    )
    row = cursor.fetchone()
    nome_varejista = row["nome_varejista"] if row else ""

    cursor.close()
    conn.close()

    # carrega pendências salvas após o último processamento
    pendencias = carregar_pendencias(cod_varejista)

    # enriquece pendências com nome automático se id_loja encontrado
    for p in pendencias:
        if not p.get("nome_pdv") and p.get("id_original"):
            p["nome_pdv"] = f"Loja {p['id_original']}"

    return templates.TemplateResponse(
        request=request,
        name="validacao.html",
        context={
            "pendencias": pendencias,
            "lojas": lojas,
            "cod_varejista": cod_varejista,
            "nome_varejista": nome_varejista,
        },
    )


@router.post("/vincular")
async def vincular_loja(dados: VincularLojaRequest):
    """Vincula manualmente um nome alias a um id_loja."""
    try:
        vincular_loja_manualmente(
            cod_varejista=dados.cod_varejista,
            nome_alias=dados.nome_alias,
            id_loja=dados.id_loja,
        )
        return JSONResponse({"ok": True, "mensagem": "Vínculo salvo com sucesso."})
    except Exception as e:
        return JSONResponse({"ok": False, "erro": str(e)}, status_code=500)
