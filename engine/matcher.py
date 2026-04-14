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
    numeros = re.findall(r'\d+', str(texto))
    return int(numeros[0]) if numeros else None


# ── Estratégias ────────────────────────────────────────────────────────────────

def _buscar_por_id_direto(cursor, id_loja):
    """Estratégia 0 — base já vem com o id_loja direto."""
    cursor.execute(
        "SELECT id_loja, nome_loja FROM loja WHERE id_loja = %s LIMIT 1",
        (id_loja,)
    )
    return cursor.fetchone()


def _buscar_por_matricula(cursor, matricula):
    """Estratégia 1 — match direto por id_loja."""
    cursor.execute(
        "SELECT id_loja, nome_loja FROM loja WHERE id_loja = %s LIMIT 1",
        (matricula,)
    )
    return cursor.fetchone()


def _buscar_por_cluster9(cursor, matricula):
    """Estratégia 2 — match pela coluna cluster_9."""
    try:
        cursor.execute(
            "SELECT id_loja, nome_loja FROM loja WHERE cluster_9 = %s LIMIT 1",
            (str(matricula),)
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
        "SELECT id_loja, nome_loja FROM loja WHERE id_loja = %s LIMIT 1",
        (numero,)
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
        (cod_varejista, nome_norm)
    )
    return cursor.fetchone()


def _salvar_alias(cursor, cod_varejista, nome_alias, id_loja):
    cursor.execute(
        """
        INSERT IGNORE INTO aliases_loja (cod_varejista, nome_alias, id_loja)
        VALUES (%s, %s, %s)
        """,
        (cod_varejista, normalizar(nome_alias), id_loja)
    )


# ── Função principal ───────────────────────────────────────────────────────────

def identificar_loja(matricula, nome_loja: str, cod_varejista: int, id_direto=None) -> dict:
    """
    Tenta identificar a loja usando 5 estratégias em ordem.
    id_direto: valor da coluna_id_direto se existir na base
    """
    conn   = get_conexao()
    cursor = conn.cursor()

    resultado  = None
    estrategia = None

    # 0 — id direto na base
    if id_direto:
        row = _buscar_por_id_direto(cursor, id_direto)
        if row:
            resultado, estrategia = row, "id_direto"

    # 1 — matrícula direta
    if not resultado and matricula:
        row = _buscar_por_matricula(cursor, matricula)
        if row:
            resultado, estrategia = row, "matricula_direta"

    # 2 — cluster_9
    if not resultado and matricula:
        row = _buscar_por_cluster9(cursor, matricula)
        if row:
            resultado, estrategia = row, "cluster_9"

    # 3 — número extraído do nome
    if not resultado and nome_loja:
        row = _buscar_por_numero_no_nome(cursor, nome_loja)
        if row:
            resultado, estrategia = row, "numero_no_nome"

    # 4 — alias salvo
    if not resultado and nome_loja:
        row = _buscar_por_alias(cursor, cod_varejista, nome_loja)
        if row:
            resultado, estrategia = row, "alias"

    # Salva alias se achou por estratégia não direta
    if resultado and estrategia in ("cluster_9", "numero_no_nome"):
        _salvar_alias(cursor, cod_varejista, nome_loja, resultado[0])
        conn.commit()

    cursor.close()
    conn.close()

    if resultado:
        return {
            "encontrado": True,
            "id_loja":    resultado[0],
            "nome_loja":  resultado[1],
            "estrategia": estrategia,
        }

    return {
        "encontrado": False,
        "id_loja":    None,
        "nome_loja":  None,
        "estrategia": None,
    }


def vincular_loja_manualmente(cod_varejista: int, nome_alias: str, id_loja: int):
    conn   = get_conexao()
    cursor = conn.cursor()
    _salvar_alias(cursor, cod_varejista, nome_alias, id_loja)
    conn.commit()
    cursor.close()
    conn.close()


# ── Cruzamento de EAN ──────────────────────────────────────────────────────────

def buscar_setor_por_ean(ean) -> str:
    """Busca setor_produto na tabela produto pelo EAN. Retorna vazio se não achar."""
    if not ean:
        return ""
    try:
        conn   = get_conexao()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT setor_produto FROM produto WHERE ean = %s LIMIT 1",
            (str(ean),)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row[0] if row and row[0] else ""
    except Exception:
        return ""