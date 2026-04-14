from pydantic import BaseModel
from typing import Optional


class VincularLojaRequest(BaseModel):
    cod_varejista: int
    nome_alias:    str
    id_loja:       int


class ProcessarRequest(BaseModel):
    cod_varejista:  int
    nome_varejista: str
    nome_arquivo:   str


class ResultadoProcessamento(BaseModel):
    ok:            bool
    arquivo_saida: Optional[str] = None
    total_linhas:  Optional[int] = None
    lojas_ok:      Optional[int] = None
    pendencias:    Optional[list] = []
    erro:          Optional[str] = None
