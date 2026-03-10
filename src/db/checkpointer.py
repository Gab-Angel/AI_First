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


def cleanup_old_checkpoints(keep: int = 1):
    """
    Para cada thread_id, mantém apenas os N checkpoints mais recentes
    e deleta o restante em cascata. Roda VACUUM após a limpeza para
    recuperar espaço em disco.

    Rodar mensalmente via APScheduler.

    Args:
        keep: Número de checkpoints a preservar por thread (padrão: 1)
    """
    conn = get_vector_conn()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT checkpoint_id
            FROM (
                SELECT checkpoint_id,
                       ROW_NUMBER() OVER (PARTITION BY thread_id ORDER BY checkpoint_id DESC) AS rn
                FROM checkpoints
            ) ranked
            WHERE rn > %s
            """,
            (keep,)
        )
        rows = cursor.fetchall()
        ids_to_delete = [row["checkpoint_id"] for row in rows]

        if not ids_to_delete:
            print(f"✅ Nenhum checkpoint elegível para limpeza (keep={keep}).")
            return

        cursor.execute(
            "DELETE FROM checkpoint_writes WHERE checkpoint_id = ANY(%s)",
            (ids_to_delete,)
        )
        writes_deleted = cursor.rowcount

        cursor.execute(
            "DELETE FROM checkpoint_blobs WHERE version = ANY(%s)",
            (ids_to_delete,)
        )
        blobs_deleted = cursor.rowcount

        cursor.execute(
            "DELETE FROM checkpoints WHERE checkpoint_id = ANY(%s)",
            (ids_to_delete,)
        )
        checkpoints_deleted = cursor.rowcount

        conn.commit()

        print(f"🗑️  Limpeza de checkpoints concluída:")
        print(f"   • Checkpoints deletados: {checkpoints_deleted}")
        print(f"   • Blobs deletados:       {blobs_deleted}")
        print(f"   • Writes deletados:      {writes_deleted}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao limpar checkpoints: {e}")

    finally:
        cursor.close()
        conn.close()

    # VACUUM fora da transação — recupera espaço físico em disco
    vacuum_conn = get_vector_conn()
    vacuum_conn.autocommit = True
    vacuum_cursor = vacuum_conn.cursor()
    try:
        print("🧹 Rodando VACUUM nas tabelas de checkpoint...")
        vacuum_cursor.execute("VACUUM FULL checkpoints")
        vacuum_cursor.execute("VACUUM FULL checkpoint_writes")
        vacuum_cursor.execute("VACUUM FULL checkpoint_blobs")
        print("✅ VACUUM concluído.")
    except Exception as e:
        print(f"❌ Erro no VACUUM: {e}")
    finally:
        vacuum_cursor.close()
        vacuum_conn.close()


def cleanup_inactive_threads(days: int = 90):
    """
    Deleta o thread completo (checkpoints + blobs + writes) de pacientes
    que não enviaram mensagem nos últimos N dias, usando chat.created_at
    como referência de inatividade.

    Isso garante que blobs também sejam removidos, controlando o crescimento
    de longo prazo do banco.

    Rodar mensalmente via APScheduler junto com cleanup_old_checkpoints.

    Args:
        days: Dias de inatividade para considerar o thread expirado (padrão: 90)
    """
    conn = get_vector_conn()
    cursor = conn.cursor()

    try:
        # Busca session_ids sem atividade no chat nos últimos N dias
        cursor.execute(
            """
            SELECT DISTINCT session_id
            FROM chat
            WHERE session_id NOT IN (
                SELECT DISTINCT session_id
                FROM chat
                WHERE created_at >= NOW() - INTERVAL '%s days'
            )
            """ % days
        )
        inactive = [row["session_id"] for row in cursor.fetchall()]

        if not inactive:
            print(f"✅ Nenhum thread inativo há mais de {days} dias.")
            return

        cursor.execute(
            "DELETE FROM checkpoint_writes WHERE thread_id = ANY(%s)",
            (inactive,)
        )
        writes_deleted = cursor.rowcount

        cursor.execute(
            "DELETE FROM checkpoint_blobs WHERE thread_id = ANY(%s)",
            (inactive,)
        )
        blobs_deleted = cursor.rowcount

        cursor.execute(
            "DELETE FROM checkpoints WHERE thread_id = ANY(%s)",
            (inactive,)
        )
        checkpoints_deleted = cursor.rowcount

        conn.commit()

        print(f"🗑️  Limpeza de threads inativos concluída:")
        print(f"   • Threads inativos:      {len(inactive)}")
        print(f"   • Checkpoints deletados: {checkpoints_deleted}")
        print(f"   • Blobs deletados:       {blobs_deleted}")
        print(f"   • Writes deletados:      {writes_deleted}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao limpar threads inativos: {e}")

    finally:
        cursor.close()
        conn.close()

    # VACUUM após deleção de threads completos
    vacuum_conn = get_vector_conn()
    vacuum_conn.autocommit = True
    vacuum_cursor = vacuum_conn.cursor()
    try:
        print("🧹 Rodando VACUUM nas tabelas de checkpoint...")
        vacuum_cursor.execute("VACUUM FULL checkpoints")
        vacuum_cursor.execute("VACUUM FULL checkpoint_writes")
        vacuum_cursor.execute("VACUUM FULL checkpoint_blobs")
        print("✅ VACUUM concluído.")
    except Exception as e:
        print(f"❌ Erro no VACUUM: {e}")
    finally:
        vacuum_cursor.close()
        vacuum_conn.close()