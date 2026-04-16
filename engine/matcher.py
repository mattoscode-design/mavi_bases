import re
import unicodedata
from engine.conexao import get_conexao


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def extrair_numero(texto: str):
    numeros = re.findall(r"\d+", str(texto))
    return int(numeros[0]) if numeros else None


def carregar_cache(cod_varejista: int) -> dict:
    """Carrega os dados de loja e aliases para evitar várias queries por linha."""
    conn = get_conexao()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id_loja, cluster_9, nome_loja FROM loja")
    lojas = cursor.fetchall()

    cursor.execute(
        "SELECT nome_alias, id_loja FROM aliases_loja WHERE cod_varejista = %s",
        (cod_varejista,),
    )
    aliases = cursor.fetchall()

    cursor.close()
    conn.close()

    cache = {
        "id_loja": {},
        "cluster_9": {},
        "alias": {},
    }

    for loja in lojas:
        chave_id = str(loja["id_loja"]).strip()
        cache["id_loja"][chave_id] = (loja["id_loja"], loja["nome_loja"])
        if loja["cluster_9"] is not None:
            chave_cluster = str(loja["cluster_9"]).strip()
            cache["cluster_9"][chave_cluster] = (loja["id_loja"], loja["nome_loja"])

    for alias in aliases:
        cache["alias"][normalizar(alias["nome_alias"])] = (
            alias["id_loja"],
            cache["id_loja"].get(str(alias["id_loja"]), (alias["id_loja"], None))[1],
        )

    return cache


# ── Estratégias ────────────────────────────────────────────────────────────────


def _buscar_por_id_direto(cursor, id_loja):
    """Estratégia 0 — base já vem com o id_loja direto."""
    cursor.execute(
        "SELECT id_loja, nome_loja FROM loja WHERE id_loja = %s LIMIT 1", (id_loja,)
    )
    return cursor.fetchone()


def _buscar_por_matricula(cursor, matricula):
    """Estratégia 1 — match direto por id_loja."""
    cursor.execute(
        "SELECT id_loja, nome_loja FROM loja WHERE id_loja = %s LIMIT 1", (matricula,)
    )
    return cursor.fetchone()


def _buscar_por_cluster9(cursor, matricula):
    """Estratégia 2 — match pela coluna cluster_9."""
    try:
        cursor.execute(
            "SELECT id_loja, nome_loja FROM loja WHERE cluster_9 = %s LIMIT 1",
            (str(matricula),),
        )
        return cursor.fetchone()
    except Exception:
        return None


def _buscar_por_numero_no_nome(cursor, nome_loja):
    """Estratégia 3 — extrai número do nome e busca em id_loja."""
    numero = extrair_numero(nome_loja)
    if numero is None:
        return None
    cursor.execute(
        "SELECT id_loja, nome_loja FROM loja WHERE id_loja = %s LIMIT 1", (numero,)
    )
    return cursor.fetchone()


def _buscar_por_alias(cursor, cod_varejista, nome_loja):
    """Estratégia 4 — alias salvo anteriormente."""
    nome_norm = normalizar(nome_loja)
    cursor.execute(
        """
        SELECT l.id_loja, l.nome_loja
        FROM aliases_loja a
        JOIN loja l ON l.id_loja = a.id_loja
        WHERE a.cod_varejista = %s AND UPPER(a.nome_alias) = %s
        LIMIT 1
        """,
        (cod_varejista, nome_norm),
    )
    return cursor.fetchone()


def _salvar_alias(cursor, cod_varejista, nome_alias, id_loja):
    cursor.execute(
        """
        INSERT IGNORE INTO aliases_loja (cod_varejista, nome_alias, id_loja)
        VALUES (%s, %s, %s)
        """,
        (cod_varejista, normalizar(nome_alias), id_loja),
    )


def salvar_aliases(cod_varejista: int, alias_list: list[tuple]) -> None:
    if not alias_list:
        return
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT IGNORE INTO aliases_loja (cod_varejista, nome_alias, id_loja) VALUES (%s, %s, %s)",
        alias_list,
    )
    conn.commit()
    cursor.close()
    conn.close()


# ── Função principal ───────────────────────────────────────────────────────────


def identificar_loja(
    matricula,
    nome_loja: str,
    cod_varejista: int,
    id_direto=None,
    cache: dict | None = None,
) -> dict:
    """
    Tenta identificar a loja usando 5 estratégias em ordem.
    id_direto: valor da coluna_id_direto se existir na base
    """
    if cache is None:
        cache = carregar_cache(cod_varejista)

    resultado = None
    estrategia = None
    nome_norm = normalizar(nome_loja) if nome_loja else ""
    matricula_str = (
        str(matricula).strip() if matricula not in (None, "", "nan", "None") else ""
    )
    id_direto_str = (
        str(id_direto).strip() if id_direto not in (None, "", "nan", "None") else ""
    )

    # 0 — id direto na base
    if id_direto_str:
        resultado = cache["id_loja"].get(id_direto_str)
        if resultado:
            estrategia = "id_direto"

    # 1 — matrícula direta
    if not resultado and matricula_str:
        resultado = cache["id_loja"].get(matricula_str)
        if resultado:
            estrategia = "matricula_direta"

    # 2 — cluster_9
    if not resultado and matricula_str:
        resultado = cache["cluster_9"].get(matricula_str)
        if resultado:
            estrategia = "cluster_9"

    # 3 — número extraído do nome
    if not resultado and nome_norm:
        numero = extrair_numero(nome_norm)
        if numero is not None:
            resultado = cache["id_loja"].get(str(numero))
            if resultado:
                estrategia = "numero_no_nome"

    # 4 — alias salvo
    if not resultado and nome_norm:
        resultado = cache["alias"].get(nome_norm)
        if resultado:
            estrategia = "alias"

    if resultado:
        return {
            "encontrado": True,
            "id_loja": resultado[0],
            "nome_loja": resultado[1],
            "estrategia": estrategia,
        }

    return {
        "encontrado": False,
        "id_loja": None,
        "nome_loja": None,
        "estrategia": None,
    }


def vincular_loja_manualmente(cod_varejista: int, nome_alias: str, id_loja: int):
    conn = get_conexao()
    cursor = conn.cursor()
    _salvar_alias(cursor, cod_varejista, nome_alias, id_loja)
    conn.commit()
    cursor.close()
    conn.close()


# ── Cruzamento de EAN ──────────────────────────────────────────────────────────


def carregar_setores_por_ean(eans: set) -> dict:
    """Retorna um dicionário ean -> setor_produto para um conjunto de EANs."""
    if not eans:
        return {}

    setores = {}
    try:
        conn = get_conexao()
        cursor = conn.cursor()

        eans_list = list({str(e).strip() for e in eans if str(e).strip()})
        if not eans_list:
            cursor.close()
            conn.close()
            return {}

        chunk_size = 800
        for i in range(0, len(eans_list), chunk_size):
            chunk = eans_list[i : i + chunk_size]
            placeholders = ", ".join(["%s"] * len(chunk))
            cursor.execute(
                f"SELECT ean, setor_produto FROM produto WHERE ean IN ({placeholders})",
                tuple(chunk),
            )
            for row in cursor.fetchall():
                if row[0] is not None:
                    setores[str(row[0]).strip()] = row[1] or ""

        cursor.close()
        conn.close()
    except Exception:
        pass

    return setores


def buscar_setor_por_ean(ean) -> str:
    """Busca setor_produto na tabela produto pelo EAN. Retorna vazio se não achar."""
    if not ean:
        return ""
    try:
        conn = get_conexao()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT setor_produto FROM produto WHERE ean = %s LIMIT 1", (str(ean),)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row[0] if row and row[0] else ""
    except Exception:
        return ""


def carregar_cache_varejistas() -> dict:
    """
    Retorna dict { nome_normalizado: {"cod": int, "nome": str} }
    para todos os varejistas cadastrados no banco.
    """
    try:
        conn = get_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT cod_varejista, nome_varejista FROM varejista")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return {
            normalizar(r["nome_varejista"]): {
                "cod": r["cod_varejista"],
                "nome": r["nome_varejista"],
            }
            for r in rows
        }
    except Exception:
        return {}
