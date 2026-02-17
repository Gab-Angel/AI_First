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
                phone_number VARCHAR(20) PRIMARY KEY,
                complete_name VARCHAR(100),
                require_human BOOLEAN NOT NULL DEFAULT FALSE,
                complete_register BOOLEAN NOT NULL DEFAULT FALSE,
                origin_contact TEXT NOT NULL DEFAULT 'whatsapp',
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
                updated_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
            );

            CREATE TABLE IF NOT EXISTS chat (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(20),
                sender VARCHAR(20)
                    CHECK (sender IN ('human', 'ai', 'user')),
                agent_name VARCHAR(50),
                message JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
            );

            CREATE TABLE IF NOT EXISTS rag_embeddings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content TEXT NOT NULL,
                category VARCHAR(100),
                embedding VECTOR(1536),
                created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
            );

            CREATE INDEX IF NOT EXISTS rag_embedding_idx
            ON rag_embeddings
            USING hnsw (embedding vector_cosine_ops);

            CREATE INDEX IF NOT EXISTS rag_category_idx
            ON rag_embeddings (category);

            CREATE TABLE IF NOT EXISTS files (
                id SERIAL PRIMARY KEY,
                category VARCHAR(100) NOT NULL,
                fileName VARCHAR(255) NOT NULL,
                mediaType VARCHAR(20) NOT NULL,
                path VARCHAR NOT NULL,
                created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
            );

            CREATE TABLE IF NOT EXISTS calendar_events (
                id SERIAL PRIMARY KEY,
                user_number VARCHAR(20) NOT NULL,
                event_id VARCHAR(255) NOT NULL UNIQUE,
                summary VARCHAR(500),
                dr_responsible VARCHAR(100),
                procedure VARCHAR(100),
                description VARCHAR(100),
                status VARCHAR(20)
                    CHECK (status IN ('pending', 'confirmed', 'canceled')),
                start_time TIMESTAMPTZ,
                end_time TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
            );

            CREATE TABLE IF NOT EXISTS token_usage (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                phone_number TEXT NOT NULL,
                message_id TEXT,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                model_name TEXT,
                provider TEXT,
                created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
            );

            CREATE TABLE doctor_rules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(150) NOT NULL,
                doctor_number VARCHAR(13),
                calendar_id VARCHAR(255) NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                procedures JSONB NOT NULL,
                duration INTEGER NOT NULL, 
                available_weekdays JSONB NOT NULL,
                working_hours JSONB NOT NULL,  
                insurances JSONB,
                restrictions JSONB,
                created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
                updated_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
            );

            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW() AT TIME ZONE 'America/Sao_Paulo';
                RETURN NEW;
            END;
            $$ language 'plpgsql';

            CREATE TRIGGER update_doctor_rules_updated_at
            BEFORE UPDATE ON doctor_rules
            FOR EACH ROW
            EXECUTE PROCEDURE update_updated_at_column();


            CREATE INDEX IF NOT EXISTS calendar_events_session_idx
            ON calendar_events (user_number);

            CREATE INDEX IF NOT EXISTS calendar_events_event_idx
            ON calendar_events (event_id);

            
            CREATE INDEX IF NOT EXISTS arquivos_categoria_idx
            ON files (category);

            CREATE INDEX IF NOT EXISTS arquivos_mediaType_idx
            ON files (mediaType);

            CREATE INDEX IF NOT EXISTS arquivos_fileName_idx
            ON files (fileName);
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
