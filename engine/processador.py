import pandas as pd
from engine import mapeamento_loader, transformador, exportador


def processar_base(
    caminho_arquivo: str, cod_varejista: int, nome_varejista: str
) -> dict:
    """
    Orquestra o processamento completo de uma base Excel.

    1. Carrega mapeamento do banco
    2. Lê o arquivo
    3. Aplica transformações
    4. Exporta o Excel tratado
    """

    # ── 1. Mapeamento ─────────────────────────────────────────────────────────
    mapeamento = mapeamento_loader.carregar(cod_varejista)

    if not mapeamento:
        return {
            "ok": False,
            "erro": f"Nenhum mapeamento configurado para '{nome_varejista}'. "
            f"Configure em /mapeamento/configurar",
        }

    # ── 2. Leitura ────────────────────────────────────────────────────────────
    try:
        df = pd.read_excel(caminho_arquivo, dtype=str)
        df.columns = df.columns.str.strip()
    except Exception as e:
        return {"ok": False, "erro": f"Erro ao ler o arquivo: {e}"}

    total_linhas = len(df)

    # ── 3. Transformações ─────────────────────────────────────────────────────

    # separar mês/ano
    if mapeamento.get("separar"):
        df = transformador.separar_mes_ano(df, mapeamento["separar"])

    # cruzar loja
    pendencias = []
    saida_id = "LOJA"
    saida_nome = "BANCO"
    if mapeamento.get("cruzar_loja"):
        df, pendencias, saida_id = transformador.cruzar_loja(
            df, mapeamento["cruzar_loja"], cod_varejista
        )
        saida_nome = mapeamento["cruzar_loja"].get("saida_nome", "BANCO")

    # cruzar ean — cria coluna nova, não toca no EAN original
    if mapeamento.get("cruzar_ean"):
        df = transformador.cruzar_ean(df, mapeamento["cruzar_ean"])

    # renomear colunas
    if mapeamento.get("renomear"):
        df = transformador.renomear_colunas(df, mapeamento["renomear"])

    # converter colunas numéricas
    colunas_calculadas = set(mapeamento.get("calcular", {}).keys())
    df = transformador.converter_numericos(df, {saida_id} | colunas_calculadas)

    # calcular colunas derivadas
    if mapeamento.get("calcular"):
        df = transformador.calcular_colunas(df, mapeamento["calcular"])

    # adicionar colunas novas
    if mapeamento.get("novas"):
        df = transformador.adicionar_colunas_novas(df, mapeamento["novas"])

    # sinalizar pendências pela coluna BANCO
    df = transformador.sinalizar_pendencias(df, pendencias, saida_nome)

    # ── 4. Exportar ───────────────────────────────────────────────────────────
    try:
        arquivo_saida = exportador.salvar_excel(df, pendencias, nome_varejista)
    except Exception as e:
        return {"ok": False, "erro": f"Erro ao salvar: {e}"}

    lojas_ok = (
        int((df[saida_nome] != "NÃO ENCONTRADO").sum())
        if saida_nome in df.columns
        else 0
    )

    return {
        "ok": True,
        "arquivo_saida": arquivo_saida,
        "total_linhas": total_linhas,
        "lojas_ok": lojas_ok,
        "pendencias": pendencias,
        "erro": None,
    }
