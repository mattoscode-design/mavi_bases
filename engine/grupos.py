"""
Gerenciamento de grupos de varejistas.
Um grupo é um conjunto nomeado de varejistas para uso no cruzar_varejista.
"""

from engine.conexao import get_conexao
from engine.logger import get_logger

_log = get_logger("grupos")
_tabelas_garantidas = False


def _garantir_tabelas():
    """Cria as tabelas de grupos caso ainda não existam — executa apenas uma vez por processo."""
    global _tabelas_garantidas
    if _tabelas_garantidas:
        return
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS varejista_grupo (
            id_grupo    INT AUTO_INCREMENT PRIMARY KEY,
            nome_grupo  VARCHAR(100) NOT NULL UNIQUE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS varejista_grupo_item (
            id_grupo      INT NOT NULL,
            cod_varejista INT NOT NULL,
            PRIMARY KEY (id_grupo, cod_varejista),
            FOREIGN KEY (id_grupo) REFERENCES varejista_grupo(id_grupo)
                ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    cursor.close()
    conn.close()
    _tabelas_garantidas = True
    _log.debug("Tabelas de grupos verificadas/criadas.")


def carregar_grupos() -> list[dict]:
    """
    Retorna lista de grupos com seus varejistas.
    [{ "id_grupo": int, "nome_grupo": str, "varejistas": [int, ...] }, ...]
    """
    try:
        _garantir_tabelas()
        conn = get_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id_grupo, nome_grupo FROM varejista_grupo ORDER BY nome_grupo"
        )
        grupos = cursor.fetchall()
        for g in grupos:
            cursor.execute(
                "SELECT cod_varejista FROM varejista_grupo_item WHERE id_grupo = %s",
                (g["id_grupo"],),
            )
            g["varejistas"] = [r["cod_varejista"] for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return grupos
    except Exception:
        return []


def salvar_grupo(nome_grupo: str, cod_varejistas: list[int]) -> int:
    """
    Cria ou atualiza um grupo. Retorna o id_grupo.
    """
    _garantir_tabelas()
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO varejista_grupo (nome_grupo) VALUES (%s) "
        "ON DUPLICATE KEY UPDATE nome_grupo = VALUES(nome_grupo)",
        (nome_grupo.strip(),),
    )
    cursor.execute(
        "SELECT id_grupo FROM varejista_grupo WHERE nome_grupo = %s",
        (nome_grupo.strip(),),
    )
    id_grupo = cursor.fetchone()[0]

    cursor.execute("DELETE FROM varejista_grupo_item WHERE id_grupo = %s", (id_grupo,))
    if cod_varejistas:
        cursor.executemany(
            "INSERT IGNORE INTO varejista_grupo_item (id_grupo, cod_varejista) VALUES (%s, %s)",
            [(id_grupo, c) for c in cod_varejistas],
        )
    conn.commit()
    cursor.close()
    conn.close()
    return id_grupo


def excluir_grupo(id_grupo: int):
    """Exclui um grupo e seus itens (CASCADE)."""
    _garantir_tabelas()
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM varejista_grupo WHERE id_grupo = %s", (id_grupo,))
    conn.commit()
    cursor.close()
    conn.close()
