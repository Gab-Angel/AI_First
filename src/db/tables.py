import time

from src.db.connection import get_vector_conn


def create_tables(retries=10, delay=3):
    for attempt in range(1, retries + 1):
        try:
            conn = get_vector_conn()
            cursor = conn.cursor()

            sql = """
            CREATE EXTENSION IF NOT EXISTS vector;
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS users (
                );

            CREATE TABLE IF NOT EXISTS chat (
                );

            CREATE TABLE IF NOT EXISTS rag_embeddings (
                );

            CREATE INDEX IF NOT EXISTS rag_embedding_idx
            ON rag_embeddings
            USING hnsw (embedding vector_cosine_ops);

            CREATE INDEX IF NOT EXISTS rag_categoria_idx
            ON rag_embeddings (categoria);

            CREATE TABLE IF NOT EXISTS files (
                );

            CREATE TABLE IF NOT EXISTS calendar_events (
                );

            CREATE TABLE IF NOT EXISTS token_usage (
                );


            CREATE INDEX IF NOT EXISTS calendar_events_session_idx
            ON calendar_events (session_id);

            CREATE INDEX IF NOT EXISTS calendar_events_event_idx
            ON calendar_events (event_id);

            
            CREATE INDEX IF NOT EXISTS arquivos_categoria_idx
            ON arquivos (categoria);

            CREATE INDEX IF NOT EXISTS arquivos_mediaType_idx
            ON arquivos (mediaType);

            CREATE INDEX IF NOT EXISTS arquivos_fileName_idx
            ON arquivos (fileName);
            """

            cursor.execute(sql)
            conn.commit()
            cursor.close()
            conn.close()

            print('✅ Banco inicializado com sucesso!')
            return

        except Exception as e:
            print(
                f'⏳ Banco não disponível (tentativa {attempt}/{retries}): {e}'
            )
            time.sleep(delay)

    raise RuntimeError(
        '❌ Não foi possível conectar ao banco após várias tentativas'
    )


def clean_tables():
    conn = get_vector_conn()
    cursor = conn.cursor()

    try:
        cursor.execute('TRUNCATE TABLE chat RESTART IDENTITY')
        cursor.execute('TRUNCATE TABLE users CASCADE')
        cursor.execute('TRUNCATE TABLE token_usage')
        # cursor.execute("TRUNCATE TABLE rag_embeddings RESTART IDENTITY")  # ← adicionar
        conn.commit()
        print('✅ Tabelas limpas com sucesso!')

    except Exception as e:
        conn.rollback()  # ← boa prática adicionar rollback
        print(f'❌ Erro ao limpar tabelas: {e}')

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    confirmacao = input(
        '⚠️  Tem certeza que deseja limpar TODAS as tabelas? (sim/não): '
    )

    if confirmacao.lower() == 'sim':
        clean_tables()
    else:
        print('❌ Operação cancelada.')
