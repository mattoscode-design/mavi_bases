import re
import pandas as pd
from engine.matcher import (
    buscar_setor_por_ean,
    carregar_cache,
    carregar_cache_varejistas,
    carregar_setores_por_ean,
    identificar_loja,
    normalizar,
    salvar_aliases,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _separar_mes_data(valor: str) -> tuple:
    """
    Converte qualquer formato de data em (MES, ANO).
    Suporta: dez./25, dez/2025, 01-01-2025, 01/01/2025,
             2025-01-01, 01-01-2025 00:00:00, 01/2025, 2025-01
    """
    MESES_TEXTO = {
        "jan": "JAN",
        "fev": "FEV",
        "mar": "MAR",
        "abr": "ABR",
        "mai": "MAI",
        "jun": "JUN",
        "jul": "JUL",
        "ago": "AGO",
        "set": "SET",
        "out": "OUT",
        "nov": "NOV",
        "dez": "DEZ",
    }
    MESES_NUM = {
        "01": "JAN",
        "02": "FEV",
        "03": "MAR",
        "04": "ABR",
        "05": "MAI",
        "06": "JUN",
        "07": "JUL",
        "08": "AGO",
        "09": "SET",
        "10": "OUT",
        "11": "NOV",
        "12": "DEZ",
    }

    if not valor or str(valor).strip() in ("", "nan", "None"):
        return "", ""

    valor_str = str(valor).strip().split(" ")[0].split("T")[0]
    valor_lower = valor_str.lower()

    for abrev, nome in MESES_TEXTO.items():
        if abrev in valor_lower:
            ano_match = re.search(r"\d{4}|\d{2}", valor_lower)
            ano = ano_match.group(0) if ano_match else ""
            if len(ano) == 2:
                ano = "20" + ano
            return nome, ano

    partes = [p.strip() for p in re.split(r"[/\-\.]", valor_str) if p.strip()]

    if len(partes) == 3:
        if len(partes[2]) == 4:
            mes_num, ano = partes[1].zfill(2), partes[2]
        elif len(partes[0]) == 4:
            mes_num, ano = partes[1].zfill(2), partes[0]
        else:
            mes_num, ano = "", ""
    elif len(partes) == 2:
        if len(partes[1]) == 4:
            mes_num, ano = partes[0].zfill(2), partes[1]
        elif len(partes[0]) == 4:
            mes_num, ano = partes[1].zfill(2), partes[0]
        else:
            mes_num, ano = "", ""
    else:
        return "", ""

    return MESES_NUM.get(mes_num, ""), ano


def _tentar_numerico(serie: pd.Series) -> pd.Series:
    """
    Tenta converter uma série string para numérico.
    Suporta formato brasileiro (1.234,56) e americano (1234.56).
    Só converte se pelo menos 80% dos valores não nulos forem numéricos.
    """

    def limpar(v):
        if pd.isna(v) or str(v).strip() == "":
            return None
        s = str(v).strip()
        # "1.234" ou "1.234.567" — separador de milhar brasileiro (ponto, sem vírgula decimal)
        if re.match(r"^-?\d{1,3}(\.\d{3})+$", s):
            s = s.replace(".", "")
        elif re.match(r"^-?[\d\.]+,\d+$", s):
            s = s.replace(".", "").replace(",", ".")
        elif re.match(r"^-?[\d,]+\.\d+$", s) or re.match(r"^-?[\d,]+$", s):
            s = s.replace(",", "")
        return s

    convertida = serie.apply(limpar)
    numerica = pd.to_numeric(convertida, errors="coerce")

    total_validos = serie.dropna().shape[0]
    total_convertido = numerica.dropna().shape[0]

    if total_validos > 0 and (total_convertido / total_validos) >= 0.8:
        return numerica

    return serie


# ── Transformações ────────────────────────────────────────────────────────────


def separar_mes_ano(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Separa coluna de data em MÊS e ANO.
    Se col_mes == col_origem, sobrescreve no lugar (não dropa).
    """
    for col_origem, destinos in cfg.items():
        if col_origem not in df.columns:
            continue
        col_mes, col_ano = destinos[0], destinos[1]
        resultado = df[col_origem].apply(_separar_mes_data)
        if col_mes:
            df[col_mes] = resultado.apply(lambda x: x[0])
        if col_ano:
            df[col_ano] = resultado.apply(lambda x: x[1])
        if col_origem != col_mes and col_origem != col_ano:
            df.drop(columns=[col_origem], inplace=True)
    return df


def cruzar_loja(df: pd.DataFrame, cfg: dict, cod_varejista: int) -> tuple:
    """
    Cruza matrícula/id com o banco usando operações vetorizadas (pandas .map).
        - Mantém a coluna original da base sem renomear
        - Cria coluna LOJA com o id_loja encontrado no banco
        - Cria coluna COD_LOJA com o id_loja encontrado (ou fallback para comparação)
    - Cria coluna BANCO com o nome da loja encontrada no banco
    - Se não achar: BANCO fica o nome PDV ou 'NÃO ENCONTRADO', e COD_LOJA fica
      com o id original para comparação visual
    Quando _COD_VAR_ existe no df usa o cod_varejista por linha para aliases.
    Retorna (df, pendencias, saida_id).
    """
    saida_id = cfg.get("saida_id", "LOJA")
    saida_nome = cfg.get("saida_nome", "BANCO")
    saida_cod = cfg.get("saida_cod", "COD_LOJA")

    col_id_direto = cfg.get("coluna_id_direto")
    col_matricula = cfg.get("coluna_matricula")
    col_nome = cfg.get("coluna_nome")

    tem_cod_var = "_COD_VAR_" in df.columns

    # ── 1. Carrega cache e achata em dicts simples ────────────────────────────
    cache_global = carregar_cache(cod_varejista)

    def _flat(cache):
        """Achata cache de tuplas (id, nome) em 6 dicts separados."""
        return (
            {k: v[0] for k, v in cache["id_loja"].items()},
            {k: v[1] for k, v in cache["id_loja"].items()},
            {k: v[0] for k, v in cache["cluster_9"].items()},
            {k: v[1] for k, v in cache["cluster_9"].items()},
            {k: v[0] for k, v in cache["alias"].items()},
            {k: v[1] for k, v in cache["alias"].items()},
        )

    id_to_id, id_to_nome, c9_to_id, c9_to_nome, alias_to_id_g, alias_to_nome_g = _flat(
        cache_global
    )

    # ── 2. Prepara séries de chave (NA onde valor é inválido) ─────────────────
    _invalidos = {"", "nan", "None"}

    def _prep(col):
        if col and col in df.columns:
            s = df[col].astype(str).str.strip()
            return s.where(~s.isin(_invalidos), other=pd.NA)
        return pd.Series(pd.NA, index=df.index, dtype=object)

    id_s = _prep(col_id_direto)
    mat_s = _prep(col_matricula)

    if col_nome and col_nome in df.columns:
        nome_s_raw = df[col_nome].astype(str).str.strip()
    else:
        nome_s_raw = pd.Series("", index=df.index, dtype=str)

    nome_norm_s = nome_s_raw.apply(
        lambda v: normalizar(v) if v and v not in _invalidos else pd.NA
    )
    # Estratégia 3: primeiro número no nome (ex: "PDV 042" → "42")
    num_from_nome = nome_s_raw.str.extract(r"(\d+)", expand=False)

    # ── 3. Estratégias 0-3 (vectorizadas, usando cache global) ───────────────
    s0_id, s0_nome = id_s.map(id_to_id), id_s.map(id_to_nome)
    s1_id, s1_nome = mat_s.map(id_to_id), mat_s.map(id_to_nome)
    s2_id, s2_nome = mat_s.map(c9_to_id), mat_s.map(c9_to_nome)
    s3_id, s3_nome = num_from_nome.map(id_to_id), num_from_nome.map(id_to_nome)

    # ── 4. Estratégia 4 (alias — varia por cod_varejista em bases consolidadas)
    if tem_cod_var:
        s4_id = pd.Series(pd.NA, index=df.index, dtype=object)
        s4_nome = pd.Series(pd.NA, index=df.index, dtype=object)
        caches_var: dict = {cod_varejista: cache_global}
        for cv, idx_g in df.groupby("_COD_VAR_").groups.items():
            cv_int = int(cv)
            if cv_int not in caches_var:
                caches_var[cv_int] = carregar_cache(cv_int)
            _, _, _, _, a_id, a_nome = _flat(caches_var[cv_int])
            s4_id.loc[idx_g] = nome_norm_s.loc[idx_g].map(a_id)
            s4_nome.loc[idx_g] = nome_norm_s.loc[idx_g].map(a_nome)
    else:
        s4_id = nome_norm_s.map(alias_to_id_g)
        s4_nome = nome_norm_s.map(alias_to_nome_g)

    # ── 5. Combina estratégias (primeira não-nula vence) ──────────────────────
    result_id = s0_id.fillna(s1_id).fillna(s2_id).fillna(s3_id).fillna(s4_id)
    result_nome = (
        s0_nome.fillna(s1_nome).fillna(s2_nome).fillna(s3_nome).fillna(s4_nome)
    )
    encontrados = result_id.notna()

    # ── 6. Salva novos aliases (cluster_9 ou numero_no_nome) ─────────────────
    used_c9 = s2_id.notna() & s0_id.isna() & s1_id.isna()
    used_num = s3_id.notna() & s0_id.isna() & s1_id.isna() & s2_id.isna()
    save_mask = (used_c9 | used_num) & nome_norm_s.notna()

    novos_aliases: set = set()
    if save_mask.any():
        cv_col = (
            df["_COD_VAR_"].astype(int)
            if tem_cod_var
            else pd.Series(cod_varejista, index=df.index)
        )
        for i in df.index[save_mask]:
            nome_v = nome_norm_s.at[i]
            id_v = result_id.at[i]
            if pd.notna(nome_v) and pd.notna(id_v):
                novos_aliases.add((int(cv_col.at[i]), str(nome_v), id_v))

    if novos_aliases:
        salvar_aliases(cod_varejista, list(novos_aliases))

    # ── 7. Monta colunas finais ───────────────────────────────────────────────
    id_original_s = id_s.fillna(mat_s)

    # COD_LOJA: se encontrou → str(id_loja); se não → id_original ou ""
    final_cod = result_id.apply(lambda v: str(v) if pd.notna(v) else None).fillna(
        id_original_s.fillna("")
    )

    # BANCO: se encontrou → nome banco; se não → nome_pdv ou "NÃO ENCONTRADO"
    nome_fallback = nome_s_raw.where(
        nome_s_raw.notna() & ~nome_s_raw.isin(_invalidos),
        other="NÃO ENCONTRADO",
    )
    final_nome = result_nome.where(encontrados, other=nome_fallback)

    # ── 8. Pendências (itera somente sobre as linhas não encontradas) ─────────
    pendencias = []
    seen: set = set()
    for i in df.index[~encontrados]:
        id_orig = str(id_original_s.at[i]) if pd.notna(id_original_s.at[i]) else ""
        nome_pdv = str(nome_s_raw.at[i]) if nome_s_raw.at[i] not in _invalidos else ""
        mat_val = ""
        if col_matricula and col_matricula in df.columns:
            v = df.at[i, col_matricula]
            mat_val = str(v).strip() if str(v) not in ("nan", "None") else ""
        chave = f"{id_orig}|{nome_pdv}"
        if chave not in seen:
            seen.add(chave)
            pendencias.append(
                {
                    "chave": chave,
                    "id_original": id_orig or "NÃO IDENTIFICADO",
                    "matricula": mat_val,
                    "nome_pdv": nome_pdv,
                    "id_loja": None,
                }
            )

    # ── 9. Aplica ao DataFrame ────────────────────────────────────────────────
    # LOJA: id do banco quando encontrado; fallback para valor original quando não encontrou
    df[saida_id] = final_cod.values
    df[saida_cod] = final_cod.values
    df[saida_nome] = final_nome.values
    df["_LOJA_OK_"] = (
        encontrados.values
    )  # flag temporária usada por sinalizar_pendencias

    return df, pendencias, saida_id


def cruzar_ean(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Cruza EAN com banco e cria coluna nova com setor_produto.
    NUNCA sobrescreve a coluna EAN original.
    """
    col_ean = cfg.get("coluna_ean")
    saida_setor = cfg.get("saida_setor", "SETOR_PRODUTO")

    # encontra coluna EAN
    col_ean_real = None
    if "EAN" in df.columns:
        col_ean_real = "EAN"
    elif col_ean and col_ean in df.columns:
        col_ean_real = col_ean

    # garante que nunca sobrescreve a coluna original
    if saida_setor == col_ean_real:
        saida_setor = "SETOR_PRODUTO"

    if col_ean_real:
        valores = df[col_ean_real].astype(str).fillna("").str.strip()
        unicos = set(valores[valores != ""].unique())
        cache = carregar_setores_por_ean(unicos)

        def buscar(ean):
            if not ean or str(ean).strip() == "":
                return ""
            return cache.get(str(ean).strip(), "NÃO IDENTIFICADO")

        df[saida_setor] = valores.map(buscar)

    return df


def cruzar_varejista(df: pd.DataFrame, cfg: dict) -> tuple:
    """
    Lê coluna de varejista da base, cruza com banco e cria coluna de saída.
    Varejistas não encontrados ficam marcados como 'NÃO ENCONTRADO' e são
    retornados como lista de pendências de varejista.

    cfg = {
        "coluna_entrada": str,
        "saida": str  (padrão "VAREJISTA_BANCO"),
        "permitidos": set[int]  (cod_varejista; vazio = aceita todos)
    }
    Retorna (df, lista_novos)
    """
    col_entrada = cfg.get("coluna_entrada")
    saida = cfg.get("saida", "VAREJISTA_BANCO")
    permitidos = cfg.get("permitidos", set())

    if not col_entrada or col_entrada not in df.columns:
        return df, []

    cache = carregar_cache_varejistas()
    if permitidos:
        cache = {k: v for k, v in cache.items() if v["cod"] in permitidos}

    # ── Vectorizado ───────────────────────────────────────────────────────────
    _invalidos = {"", "nan", "None"}
    vals = df[col_entrada].astype(str).str.strip()

    norm_series = vals.apply(lambda v: normalizar(v) if v not in _invalidos else pd.NA)

    nome_map = {k: v["nome"] for k, v in cache.items()}
    cod_map = {k: v["cod"] for k, v in cache.items()}

    nomes_saida = norm_series.map(nome_map).where(norm_series.notna(), other="")
    cods_saida = (
        norm_series.map(cod_map)
        .where(norm_series.notna(), other=0)
        .fillna(0)
        .astype(int)
    )

    # onde cache não achou → "NÃO ENCONTRADO" (notna + nome ausente)
    nao_vazio = norm_series.notna()
    nao_achou = nao_vazio & nomes_saida.isna()
    nomes_saida = (
        nomes_saida.fillna(
            vals.where(nao_achou, other="").where(
                ~nao_achou | vals.isin(_invalidos), other="NÃO ENCONTRADO"
            )
        )
        .where(nao_vazio, other="")
        .fillna("")
    )

    # lista de novos (únicos)
    novos = list(vals[nao_achou].unique())

    df[saida] = nomes_saida.values
    df["_COD_VAR_"] = cods_saida.values  # coluna temporária para cruzar_loja
    return df, novos


def renomear_colunas(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Renomeia colunas conforme mapeamento."""
    return df.rename(columns=cfg)


def converter_numericos(df: pd.DataFrame, colunas_protegidas: set) -> pd.DataFrame:
    """
    Converte automaticamente colunas numéricas.
    Preserva colunas de texto esperado.
    """
    texto_fixo = {
        "BANCO",
        "PENDENCIA",
        "MÊS",
        "ANO",
        "DATA",
        "SETOR_PRODUTO",
        "NOME_VAREJISTA",
    }
    protegidas = colunas_protegidas | texto_fixo

    for col in df.columns:
        if col in protegidas:
            continue
        df[col] = _tentar_numerico(df[col])

    return df


def calcular_colunas(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Calcula colunas derivadas (ex: QUANTIDADE = VALOR / PRECO)."""
    for col_saida, (col_a, operador, col_b) in cfg.items():
        if col_a not in df.columns or col_b not in df.columns:
            continue
        # nunca sobrescrever uma coluna que é insumo do cálculo
        dest = col_saida if col_saida not in (col_a, col_b) else col_saida + "_CALC"
        serie_a = pd.to_numeric(df[col_a], errors="coerce")
        serie_b = pd.to_numeric(df[col_b], errors="coerce")
        if operador == "/":
            df[dest] = (serie_a / serie_b.replace(0, None)).round(4)
        elif operador == "*":
            df[dest] = (serie_a * serie_b).round(4)
        elif operador == "+":
            df[dest] = (serie_a + serie_b).round(4)
        elif operador == "-":
            df[dest] = (serie_a - serie_b).round(4)
    return df


def adicionar_colunas_novas(
    df: pd.DataFrame, novas: list, rename_map: dict | None = None
) -> pd.DataFrame:
    """Adiciona colunas novas (vazia, valor fixo, ano atual, calcular_quantidade)."""
    rename_map = rename_map or {}

    def _resolver(col: str) -> str:
        """Retorna o nome real da coluna no df: original ou pós-renomeação."""
        if col in df.columns:
            return col
        renamed = rename_map.get(col)
        if renamed and renamed in df.columns:
            return renamed
        return col

    for nova in novas:
        col_saida = nova["coluna_saida"]
        tipo = nova["tipo_acao"]
        formula = nova.get("formula", "")

        if tipo == "vazia":
            df[col_saida] = ""
        elif tipo == "valor_fixo":
            df[col_saida] = formula
        elif tipo == "ano_atual":
            df[col_saida] = pd.Timestamp.now().year
        elif tipo == "calcular_quantidade":
            if "/" in formula:
                partes = formula.split("/", 1)
                col_a = _resolver(partes[0].strip())
                col_b = _resolver(partes[1].strip())
                if col_a in df.columns and col_b in df.columns:
                    # nunca sobrescrever uma coluna que é insumo do cálculo
                    dest = (
                        col_saida
                        if col_saida not in (col_a, col_b)
                        else col_saida + "_CALC"
                    )
                    ser_a = pd.to_numeric(df[col_a], errors="coerce")
                    ser_b = pd.to_numeric(df[col_b], errors="coerce")
                    df[dest] = (ser_a / ser_b.replace(0, None)).round(4)

    return df


def sinalizar_pendencias(
    df: pd.DataFrame, pendencias: list, saida_nome: str
) -> pd.DataFrame:
    """Adiciona coluna PENDENCIA com base na flag _LOJA_OK_ gerada por cruzar_loja."""
    if "_LOJA_OK_" in df.columns:
        df["PENDENCIA"] = df["_LOJA_OK_"].apply(
            lambda ok: "IDENTIFICADA" if ok else "LOJA NAO IDENTIFICADA"
        )
        df.drop(columns=["_LOJA_OK_"], inplace=True)
    elif saida_nome in df.columns:
        # fallback para bases sem cruzar_loja
        df["PENDENCIA"] = df[saida_nome].apply(
            lambda v: (
                "LOJA NAO IDENTIFICADA" if v == "NÃO ENCONTRADO" else "IDENTIFICADA"
            )
        )
    return df
