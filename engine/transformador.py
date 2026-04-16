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
    Cruza matrícula/id com o banco:
    - Renomeia a coluna original para LOJA (mantém valor original da base)
    - Cria coluna COD_LOJA com o id_loja encontrado no banco
    - Cria coluna BANCO com o nome da loja encontrada no banco
    - Se não achar: BANCO fica 'NÃO ENCONTRADO' e sinaliza como pendência
    Quando _COD_VAR_ existe no df usa o cod_varejista por linha para aliases.
    Retorna (df, pendencias, saida_id).
    """
    pendencias = []
    saida_id = cfg.get("saida_id", "LOJA")
    saida_nome = cfg.get("saida_nome", "BANCO")
    saida_cod = cfg.get("saida_cod", "COD_LOJA")

    col_id_direto = cfg.get("coluna_id_direto")
    col_matricula = cfg.get("coluna_matricula")
    col_nome = cfg.get("coluna_nome")
    col_original = col_id_direto or col_matricula or col_nome

    # detecta se temos varejistas por linha (base consolidada)
    tem_cod_var = "_COD_VAR_" in df.columns

    nomes_banco = []
    cods_loja = []
    encontrados = []  # True = loja identificada, False = pendência
    ids_pendentes = set()
    novos_aliases = set()
    cache_global = carregar_cache(cod_varejista)
    # cache por varejista específico (para aliases corretos em bases consolidadas)
    cache_por_var: dict = {}

    def _get_cache(cv: int):
        if cv == 0 or cv == cod_varejista:
            return cache_global
        if cv not in cache_por_var:
            cache_por_var[cv] = carregar_cache(cv)
        return cache_por_var[cv]

    cols = list(df.columns)
    idx_id_direto = cols.index(col_id_direto) if col_id_direto in cols else None
    idx_matricula = cols.index(col_matricula) if col_matricula in cols else None
    idx_nome = cols.index(col_nome) if col_nome in cols else None
    idx_cod_var = cols.index("_COD_VAR_") if tem_cod_var else None

    for row in df.itertuples(index=False, name=None):
        id_direto = row[idx_id_direto] if idx_id_direto is not None else None
        matricula = row[idx_matricula] if idx_matricula is not None else None
        nome_pdv = row[idx_nome] if idx_nome is not None else ""
        cv = int(row[idx_cod_var]) if idx_cod_var is not None else cod_varejista

        # captura id original de forma segura
        id_original = None
        if id_direto is not None and str(id_direto).strip() not in ("", "nan", "None"):
            id_original = str(id_direto).strip()
        elif matricula is not None and str(matricula).strip() not in (
            "",
            "nan",
            "None",
        ):
            id_original = str(matricula).strip()

        cache_linha = _get_cache(cv)
        resultado = identificar_loja(
            matricula,
            nome_pdv,
            cv if tem_cod_var else cod_varejista,
            id_direto=id_direto,
            cache=cache_linha,
        )

        if resultado["encontrado"]:
            nomes_banco.append(resultado["nome_loja"])
            cods_loja.append(
                str(resultado["id_loja"]) if resultado["id_loja"] is not None else ""
            )
            encontrados.append(True)
            if resultado["estrategia"] in ("cluster_9", "numero_no_nome") and nome_pdv:
                novos_aliases.add(
                    (
                        cv if tem_cod_var else cod_varejista,
                        normalizar(nome_pdv),
                        resultado["id_loja"],
                    )
                )
        else:
            # mantém nome e id originais da base para comparação visual na saída
            nomes_banco.append(
                str(nome_pdv).strip()
                if nome_pdv and str(nome_pdv).strip() not in ("", "nan", "None")
                else "NÃO ENCONTRADO"
            )
            # mantém o id original para comparação visual na saída
            cods_loja.append(id_original or "")
            encontrados.append(False)
            chave_pend = f"{id_original}|{nome_pdv}"
            if chave_pend not in ids_pendentes:
                ids_pendentes.add(chave_pend)
                pendencias.append(
                    {
                        "chave": chave_pend,
                        "id_original": id_original or "NÃO IDENTIFICADO",
                        "matricula": (
                            str(matricula).strip()
                            if matricula and str(matricula) not in ("nan", "None")
                            else ""
                        ),
                        "nome_pdv": nome_pdv,
                        "id_loja": resultado.get("id_loja"),
                    }
                )

    if novos_aliases:
        salvar_aliases(cod_varejista, list(novos_aliases))

    if col_original and col_original in df.columns and col_original != saida_id:
        df.rename(columns={col_original: saida_id}, inplace=True)

    df[saida_cod] = cods_loja
    df[saida_nome] = nomes_banco
    df["_LOJA_OK_"] = encontrados  # flag temporária usada por sinalizar_pendencias

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

    nomes_saida = []
    cods_saida = []
    novos = []
    vistos = set()

    for val in df[col_entrada].astype(str).str.strip():
        if val in ("", "nan", "None"):
            nomes_saida.append("")
            cods_saida.append(0)
            continue
        norm = normalizar(val)
        match = cache.get(norm)
        if match:
            nomes_saida.append(match["nome"])
            cods_saida.append(match["cod"])
        else:
            nomes_saida.append("NÃO ENCONTRADO")
            cods_saida.append(0)
            if val not in vistos:
                vistos.add(val)
                novos.append(val)

    df[saida] = nomes_saida
    df["_COD_VAR_"] = cods_saida  # coluna temporária para cruzar_loja
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
