import time
import pandas as pd
from engine import mapeamento_loader, transformador, exportador


def processar_base(
    caminho_arquivo: str,
    cod_varejista: int,
    nome_varejista: str,
    on_status=None,
) -> dict:
    """
    Orquestra o processamento completo de uma base Excel.

    Retorna dict com:
    - ok, erro
    - arquivo_saida
    - total_linhas
    - lojas_unicas      ← total de lojas únicas na base
    - lojas_ok          ← lojas identificadas no banco
    - lojas_novas       ← lojas não encontradas
    - total_valor       ← soma da coluna VALOR
    - total_quantidade  ← soma da coluna QUANTIDADE
    - setores           ← lista de setores únicos de SETOR_PRODUTO
    - pendencias
    """

    # Pesos cumulativos de progresso (0.0 – 1.0) por etapa
    _PESOS = {
        "Carregando mapeamento...": 0.05,
        "Lendo arquivo Excel...": 0.15,
        "Removendo colunas ignoradas...": 0.17,
        "Separando data em MÊS e ANO...": 0.20,
        "Identificando lojas...": 0.58,
        "Cruzando varejistas...": 0.64,
        "Cruzando EANs...": 0.70,
        "Renomeando colunas...": 0.72,
        "Convertendo valores numéricos...": 0.78,
        "Calculando colunas...": 0.82,
        "Adicionando novas colunas...": 0.85,
        "Sinalizando pendências...": 0.88,
        "Exportando arquivo Excel...": 1.00,
    }

    def _status(msg: str):
        if on_status:
            try:
                on_status(msg, _PESOS.get(msg))
            except Exception:
                pass

    timings = {}
    inicio_total = time.perf_counter()

    # ── 1. Mapeamento ─────────────────────────────────────────────────────────
    _status("Carregando mapeamento...")
    inicio = time.perf_counter()
    mapeamento = mapeamento_loader.carregar(cod_varejista)
    timings["load_mapping"] = time.perf_counter() - inicio

    if not mapeamento:
        return {
            "ok": False,
            "erro": f"Nenhum mapeamento configurado para '{nome_varejista}'. "
            f"Configure em Configurar Mapeamento.",
        }

    # ── 2. Leitura ────────────────────────────────────────────────────────────
    try:
        _status("Lendo arquivo Excel...")
        inicio = time.perf_counter()
        df = pd.read_excel(caminho_arquivo, dtype=str)
        df.columns = df.columns.str.strip()
        timings["read_excel"] = time.perf_counter() - inicio
    except Exception as e:
        return {"ok": False, "erro": f"Erro ao ler o arquivo: {e}"}

    total_linhas = len(df)

    # ── 3. Colunas a ignorar (remove antes de processar) ──────────────────────
    _status("Removendo colunas ignoradas...")
    inicio = time.perf_counter()
    colunas_ignorar = [
        col for col in mapeamento.get("ignorar", []) if col in df.columns
    ]
    if colunas_ignorar:
        df.drop(columns=colunas_ignorar, inplace=True)
    timings["drop_ignored"] = time.perf_counter() - inicio

    # ── 4. Transformações ─────────────────────────────────────────────────────

    if mapeamento.get("separar"):
        _status("Separando data em MÊS e ANO...")
        inicio = time.perf_counter()
        df = transformador.separar_mes_ano(df, mapeamento["separar"])
        timings["separar_mes_ano"] = time.perf_counter() - inicio

    pendencias = []
    saida_id = "LOJA"
    saida_nome = "BANCO"
    if mapeamento.get("cruzar_loja"):
        _status("Identificando lojas...")
        inicio = time.perf_counter()
        df, pendencias, saida_id = transformador.cruzar_loja(
            df, mapeamento["cruzar_loja"], cod_varejista
        )
        timings["cruzar_loja"] = time.perf_counter() - inicio
        saida_nome = mapeamento["cruzar_loja"].get("saida_nome", "BANCO")

    varejistas_novos = []
    if mapeamento.get("cruzar_varejista"):
        _status("Cruzando varejistas...")
        inicio = time.perf_counter()
        df, varejistas_novos = transformador.cruzar_varejista(
            df, mapeamento["cruzar_varejista"]
        )
        timings["cruzar_varejista"] = time.perf_counter() - inicio

    if mapeamento.get("cruzar_ean"):
        _status("Cruzando EANs...")
        inicio = time.perf_counter()
        df = transformador.cruzar_ean(df, mapeamento["cruzar_ean"])
        timings["cruzar_ean"] = time.perf_counter() - inicio

    if mapeamento.get("renomear"):
        _status("Renomeando colunas...")
        inicio = time.perf_counter()
        df = transformador.renomear_colunas(df, mapeamento["renomear"])
        timings["renomear"] = time.perf_counter() - inicio

    colunas_calculadas = set(mapeamento.get("calcular", {}).keys())
    _status("Convertendo valores numéricos...")
    df = transformador.converter_numericos(df, {saida_id} | colunas_calculadas)

    if mapeamento.get("calcular"):
        _status("Calculando colunas...")
        inicio = time.perf_counter()
        df = transformador.calcular_colunas(df, mapeamento["calcular"])
        timings["calcular"] = time.perf_counter() - inicio

    if mapeamento.get("novas"):
        _status("Adicionando novas colunas...")
        inicio = time.perf_counter()
        df = transformador.adicionar_colunas_novas(df, mapeamento["novas"])
        timings["adicionar_novas"] = time.perf_counter() - inicio

    _status("Sinalizando pendências...")
    inicio = time.perf_counter()
    df = transformador.sinalizar_pendencias(df, pendencias, saida_nome)
    timings["sinalizar_pendencias"] = time.perf_counter() - inicio

    # ── 5. Estatísticas ───────────────────────────────────────────────────────

    # total valor
    total_valor = 0.0
    if "VALOR" in df.columns:
        total_valor = pd.to_numeric(df["VALOR"], errors="coerce").sum()
        total_valor = round(float(total_valor), 2) if not pd.isna(total_valor) else 0.0

    # total quantidade
    total_quantidade = 0.0
    if "QUANTIDADE" in df.columns:
        total_quantidade = pd.to_numeric(df["QUANTIDADE"], errors="coerce").sum()
        total_quantidade = (
            round(float(total_quantidade), 2) if not pd.isna(total_quantidade) else 0.0
        )

    # setores únicos
    setores = []
    if "SETOR_PRODUTO" in df.columns:
        setores = [
            s
            for s in df["SETOR_PRODUTO"].dropna().unique().tolist()
            if s and s != "NÃO IDENTIFICADO"
        ]
        setores = sorted(setores)

    # lojas únicas identificadas
    lojas_unicas = 0
    lojas_ok = 0
    if saida_id in df.columns:
        lojas_unicas = df[saida_id].nunique()

    if saida_nome in df.columns and saida_id in df.columns:
        lojas_ok = int(
            df.loc[df[saida_nome] != "NÃO ENCONTRADO", saida_id]
            .dropna()
            .astype(str)
            .nunique()
        )

    lojas_novas = len(pendencias)

    # ── 6. Exportar ───────────────────────────────────────────────────────────
    _status("Exportando arquivo Excel...")
    try:
        inicio = time.perf_counter()
        arquivo_saida = exportador.salvar_excel(df, pendencias, nome_varejista)
        timings["exportar"] = time.perf_counter() - inicio
    except Exception as e:
        return {"ok": False, "erro": f"Erro ao salvar: {e}"}

    timings["total"] = time.perf_counter() - inicio_total

    return {
        "ok": True,
        "arquivo_saida": arquivo_saida,
        "total_linhas": total_linhas,
        "lojas_unicas": int(lojas_unicas),
        "lojas_ok": lojas_ok,
        "lojas_novas": lojas_novas,
        "total_valor": total_valor,
        "total_quantidade": total_quantidade,
        "setores": setores,
        "pendencias": pendencias,
        "varejistas_novos": varejistas_novos,
        "erro": None,
        "timings": timings,
    }
