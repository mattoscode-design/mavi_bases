from pydantic import BaseModel
from typing import Optional


class VincularLojaRequest(BaseModel):
    cod_varejista: int
    nome_alias: str
    id_loja: int


class ProcessarRequest(BaseModel):
    cod_varejista: int
    nome_varejista: str
    nome_arquivo: str


class ResultadoProcessamento(BaseModel):
    ok: bool
    arquivo_saida: Optional[str] = None
    total_linhas: Optional[int] = None
    lojas_unicas: Optional[int] = None
    lojas_ok: Optional[int] = None
    lojas_novas: Optional[int] = None
    total_valor: Optional[float] = None
    total_quantidade: Optional[float] = None
    setores: Optional[list] = []
    pendencias: Optional[list] = []
    varejistas_novos: Optional[list] = []
    mes_ref: Optional[str] = ""
    coluna_varejista_saida: Optional[str] = ""
    erro: Optional[str] = None
    timings: Optional[dict] = {}
