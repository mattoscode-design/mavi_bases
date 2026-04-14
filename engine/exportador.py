import os
import pandas as pd
from config import PASTA_SAIDA


def salvar_excel(df: pd.DataFrame, pendencias: list, nome_varejista: str) -> str:
    """
    Salva o DataFrame tratado em Excel na pasta saidas/.
    Cria aba LOJAS NOVAS se houver pendências.
    Retorna o nome do arquivo gerado.
    """
    nome_arquivo = (
        f"{nome_varejista}_tratado_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
    caminho = os.path.join(PASTA_SAIDA, nome_arquivo)

    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="BASE_TRATADA")

        if pendencias:
            df_pend = pd.DataFrame(pendencias).drop(columns=["chave"])
            df_pend.rename(
                columns={
                    "id_original": "ID DA BASE",
                    "matricula": "MATRÍCULA",
                    "nome_pdv": "NOME PDV",
                    "id_loja": "ID LOJA BANCO",
                },
                inplace=True,
            )
            df_pend.to_excel(writer, index=False, sheet_name="LOJAS NOVAS")

    return nome_arquivo
