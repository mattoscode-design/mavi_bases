import re
import pandas as pd
from engine.matcher import identificar_loja, buscar_setor_por_ean


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
        if re.match(r"^-?[\d\.]+,\d+$", s):
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
    - Cria coluna BANCO com o nome da loja encontrada no banco
    - Se não achar: BANCO fica 'NÃO ENCONTRADO' e sinaliza como pendência
    Retorna (df, pendencias, saida_id).
    """
    pendencias = []
    saida_id = cfg.get("saida_id", "LOJA")
    saida_nome = cfg.get("saida_nome", "BANCO")

    col_id_direto = cfg.get("coluna_id_direto")
    col_matricula = cfg.get("coluna_matricula")
    col_nome = cfg.get("coluna_nome")
    col_original = col_id_direto or col_matricula

    nomes_banco = []
    ids_pendentes = set()

    for _, row in df.iterrows():
        id_direto = (
            row.get(col_id_direto)
            if col_id_direto and col_id_direto in df.columns
            else None
        )
        matricula = (
            row.get(col_matricula)
            if col_matricula and col_matricula in df.columns
            else None
        )
        nome_pdv = row.get(col_nome, "") if col_nome and col_nome in df.columns else ""

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

        resultado = identificar_loja(
            matricula, nome_pdv, cod_varejista, id_direto=id_direto
        )

        if resultado["encontrado"]:
            nomes_banco.append(resultado["nome_loja"])
        else:
            nomes_banco.append("NÃO ENCONTRADO")
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

    # renomeia coluna original para LOJA (mantém o valor que veio da base)
    if col_original and col_original in df.columns and col_original != saida_id:
        df.rename(columns={col_original: saida_id}, inplace=True)

    # adiciona coluna BANCO com nome do banco
    df[saida_nome] = nomes_banco

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

        def buscar(ean):
            resultado = buscar_setor_por_ean(ean)
            return resultado if resultado else "NÃO IDENTIFICADO"

        df[saida_setor] = df[col_ean_real].apply(buscar)

    return df


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
        serie_a = pd.to_numeric(df[col_a], errors="coerce")
        serie_b = pd.to_numeric(df[col_b], errors="coerce")
        if operador == "/":
            df[col_saida] = (serie_a / serie_b.replace(0, None)).round(4)
        elif operador == "*":
            df[col_saida] = (serie_a * serie_b).round(4)
        elif operador == "+":
            df[col_saida] = (serie_a + serie_b).round(4)
        elif operador == "-":
            df[col_saida] = (serie_a - serie_b).round(4)
    return df


def adicionar_colunas_novas(df: pd.DataFrame, novas: list) -> pd.DataFrame:
    """Adiciona colunas novas (vazia, valor fixo, ano atual)."""
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

    return df


def sinalizar_pendencias(
    df: pd.DataFrame, pendencias: list, saida_nome: str
) -> pd.DataFrame:
    """Adiciona coluna PENDENCIA nas linhas com BANCO = NÃO ENCONTRADO."""
    if pendencias and saida_nome in df.columns:
        df["PENDENCIA"] = df[saida_nome].apply(
            lambda v: "LOJA NAO IDENTIFICADA" if v == "NÃO ENCONTRADO" else ""
        )
    return df
