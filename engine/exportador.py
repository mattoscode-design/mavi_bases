import importlib.util
import os
import tempfile
import pandas as pd
from engine.logger import get_logger

_log = get_logger("exportador")


def salvar_excel(df: pd.DataFrame, pendencias: list, nome_varejista: str) -> str:
    """
    Salva o DataFrame tratado em um arquivo Excel temporário.
    Retorna o caminho completo do arquivo (em temp do sistema).
    O chamador é responsável por copiar/mover e depois deletar.
    """
    engine = "xlsxwriter" if importlib.util.find_spec("xlsxwriter") else "openpyxl"
    suffix = f"_{nome_varejista}_BASE.xlsx"

    # delete=False para poder passar o caminho adiante antes de copiar
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    caminho = tmp.name
    tmp.close()

    def _escrever(eng):
        with pd.ExcelWriter(caminho, engine=eng) as writer:
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

    try:
        try:
            _escrever(engine)
        except Exception:
            if engine == "xlsxwriter":
                _log.warning("xlsxwriter falhou, tentando openpyxl.")
                _escrever("openpyxl")
            else:
                raise
    except Exception as e:
        _log.error(
            "Falha ao escrever Excel temporário '%s': %s", caminho, e, exc_info=True
        )
        try:
            os.unlink(caminho)
        except OSError:
            pass
        raise

    return caminho
