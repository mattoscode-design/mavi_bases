import mysql.connector
from mysql.connector import Error, pooling
from config import DB_CONFIG

# Pool de conexões para reutilizar sem abrir/fechar a cada query
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="agente_pool",
            pool_size=5,
            **DB_CONFIG
        )
    return _pool


def get_conexao():
    """Retorna uma conexão do pool."""
    try:
        return get_pool().get_connection()
    except Error as e:
        raise RuntimeError(f"Erro ao conectar no banco: {e}")


def testar_conexao() -> dict:
    """Testa a conexão e retorna status."""
    try:
        conn = get_conexao()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        versao = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return {"ok": True, "versao": versao}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


if __name__ == "__main__":
    resultado = testar_conexao()
    if resultado["ok"]:
        print(f"✅ Conectado ao MySQL {resultado['versao']}")
    else:
        print(f"❌ Erro: {resultado['erro']}")
