from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from engine.conexao import testar_conexao
from routers import upload, validacao, resultado, mapeamento


app = FastAPI(
    title="Agente de Bases",
    description="Processamento e tratamento de bases Excel por varejista",
    version="1.0.0",
)

# ── Arquivos estáticos ─────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(validacao.router)
app.include_router(resultado.router)
app.include_router(mapeamento.router)


# ── Evento de inicialização ────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    status = testar_conexao()
    if status["ok"]:
        print(f"✅ Banco conectado — MySQL {status['versao']}")
    else:
        print(f"❌ Falha na conexão com o banco: {status['erro']}")
        print("   Verifique as credenciais no arquivo .env")


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    db = testar_conexao()
    return {"status": "ok", "banco": db}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
