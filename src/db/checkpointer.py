import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from src.db.connection import get_vector_conn

load_dotenv()

DB_URI = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)


def get_checkpointer() -> PostgresSaver:
    """
    Retorna uma instância do PostgresSaver pronta para uso.
    Deve ser usado como context manager no graph.invoke:

        with get_checkpointer() as checkpointer:
            graph = workflow.compile(checkpointer=checkpointer)
    """
    return PostgresSaver.from_conn_string(DB_URI)


def setup_checkpointer():
    """
    Cria as tabelas do checkpointer no PostgreSQL.
    Chamar apenas uma vez no lifespan do FastAPI junto com create_tables().
    """
    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        checkpointer.setup()
        print("✅ Tabelas do checkpointer criadas com sucesso!")


def cleanup_checkpointer(days: int = 30):
    """
    Remove checkpoints de threads sem atividade nos últimos N dias.
    Limpa em cascata: checkpoints → checkpoint_blobs → checkpoint_writes.

    Recomendado: rodar periodicamente via cron ou agendador.

    Args:
        days: Dias de inatividade para considerar o thread expirado (padrão: 30)
    """
    conn = get_vector_conn()
    cursor = conn.cursor()

    try:
        # Identifica threads expirados
        cursor.execute(
            """
            SELECT DISTINCT thread_id
            FROM checkpoints
            WHERE ts < NOW() - INTERVAL '%s days'
            """,
            (days,)
        )
        threads = [row['thread_id'] for row in cursor.fetchall()]

        if not threads:
            print(f"✅ Nenhum checkpoint com mais de {days} dias encontrado.")
            return

        # Remove em cascata pelas 3 tabelas
        cursor.execute(
            "DELETE FROM checkpoint_writes WHERE thread_id = ANY(%s)",
            (threads,)
        )
        writes_deleted = cursor.rowcount

        cursor.execute(
            "DELETE FROM checkpoint_blobs WHERE thread_id = ANY(%s)",
            (threads,)
        )
        blobs_deleted = cursor.rowcount

        cursor.execute(
            "DELETE FROM checkpoints WHERE thread_id = ANY(%s)",
            (threads,)
        )
        checkpoints_deleted = cursor.rowcount

        conn.commit()

        print(f"🗑️  Limpeza de checkpoints concluída:")
        print(f"   • Threads removidos:     {len(threads)}")
        print(f"   • Checkpoints deletados: {checkpoints_deleted}")
        print(f"   • Blobs deletados:       {blobs_deleted}")
        print(f"   • Writes deletados:      {writes_deleted}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao limpar checkpoints: {e}")

    finally:
        cursor.close()
        conn.close()