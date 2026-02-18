import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.db.connection import get_vector_conn


class PostgreSQL:
    @staticmethod
    def verify_user(phone_number: str) -> bool:
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT 1
                FROM users
                WHERE phone_number = %s
                """,
                (phone_number,),
            )
            return cursor.fetchone() is not None

        except Exception as e:
            print(f'❌ Erro ao verificar usuário: {e}')
            return False

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def verify_cadastro(phone_number: str) -> bool:
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT complete_register
                FROM users
                WHERE phone_number = %s
                """,
                (phone_number,),
            )
            result = cursor.fetchone()
            return result['complete_register'] if result else False

        except Exception as e:
            print(f'❌ Erro ao buscar status cadastro: {e}')
            return False

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_user(phone_number: str, origin_contact: str = 'whatsapp'):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users (phone_number, origin_contact)
                VALUES (%s, %s)
                ON CONFLICT (phone_number) DO NOTHING
                """,
                (phone_number, origin_contact),
            )
            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f'❌ Erro ao criar usuário: {e}')

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_user(
        phone_number: str,
        complete_name: str | None = None,
        cpf: str | None = None,
        convenio: str | None = None,
        complete_register: bool | None = None,
        metadata: dict | None = None,
    ):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE users
                SET
                    complete_name = COALESCE(%s, complete_name),
                    cpf = COALESCE(%s, cpf),
                    convenio = COALESCE(%s, convenio),
                    complete_register = COALESCE(%s, complete_register),
                    metadata = COALESCE(%s, metadata)
                WHERE phone_number = %s
                """,
                (
                    complete_name,
                    cpf,
                    convenio,
                    complete_register,
                    json.dumps(metadata) if metadata else None,
                    phone_number,
                ),
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f'❌ Erro ao atualizar usuário: {e}')

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def finally_user(phone_number: str):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE users
                SET complete_register = %s
                WHERE phone_number = %s
                """,
                (True, phone_number),
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f'❌ Erro ao finalizar usuário: {e}')

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_require_human(phone_number: str):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE users
                SET require_human = %s
                WHERE phone_number = %s
                """,
                (True, phone_number),
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f'❌ Erro ao atualizar require_human: {e}')

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def save_message(session_id: str, sender: str, message: dict, agent_name: str = None):

        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO chat (session_id, sender, agent_name, message)
                VALUES (%s, %s, %s, %s)
            """,
                (session_id, sender, agent_name, json.dumps(message)),
            )

            conn.commit()
            print('✅ Mensagem salva com sucesso')

        except Exception as e:
            conn.rollback()
            print(f'❌ Erro ao salvar mensagem no banco: {e}')

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_historico(number: str):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT message
                FROM (
                    SELECT message, created_at
                    FROM chat
                    WHERE session_id = %s
                    ORDER BY created_at DESC
                    LIMIT 20
                ) t
                ORDER BY created_at ASC
                """,
                (number,),
            )

            rows = cursor.fetchall()
            historico = []

            for row in rows:
                msg = row['message']

                if msg['type'] == 'human':
                    historico.append(HumanMessage(content=msg['content']))

                elif msg['type'] == 'ai':
                    historico.append(AIMessage(content=msg['content']))

                elif msg['type'] == 'tool_calls':
                    historico.append(
                        AIMessage(
                            content='',
                            tool_calls=msg['content']
                        )
                    )

                elif msg['type'] == 'tool':
                    historico.append(
                        ToolMessage(
                            content=msg['content'],
                            tool_call_id=msg.get('tool_call_id', ''),
                        )
                    )

            return historico

        except Exception as e:
            print(f'❌ Erro ao recuperar histórico: {e}')
            return []

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_file(categoria: str):

        try:
            conn = get_vector_conn()
            cursor = conn.cursor()

            query = """
                SELECT category, fileName, mediaType, path
                FROM files
                WHERE category ILIKE %s
                LIMIT 1;
            """

            termo = f'%{categoria}%'
            cursor.execute(query, (termo,))

            resultado = cursor.fetchone()
            return resultado

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def save_calendar_event(
        user_number: str,
        event_id: str,
        summary: str,
        dr_responsible: str,
        procedure: str,
        start_time: str,
        end_time: str,
        description: str = ""
    ):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO calendar_events (
                    user_number, event_id, summary, procedure,
                    dr_responsible, start_time, end_time, description
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s AT TIME ZONE 'America/Sao_Paulo',
                    %s AT TIME ZONE 'America/Sao_Paulo',
                    %s
                )
                """,
                (user_number, event_id, summary, procedure, dr_responsible, start_time, end_time, description),
            )
            conn.commit()
            print(f'✅ Evento {event_id} salvo no banco')

        except Exception as e:
            conn.rollback()
            print(f'❌ Erro ao salvar evento: {e}')

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_calendar_events(user_number: str):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT event_id, summary, start_time, end_time, description, created_at
                FROM calendar_events
                WHERE user_number = %s
                ORDER BY start_time ASC
                """,
                (user_number,),
            )

            rows = cursor.fetchall()
            return rows

        except Exception as e:
            print(f'❌ Erro ao buscar eventos: {e}')
            return []

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete_calendar_event(user_number: str, event_id: str):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                DELETE FROM calendar_events
                WHERE user_number = %s AND event_id = %s
                """,
                (user_number, event_id),
            )
            conn.commit()

            if cursor.rowcount > 0:
                print(f'✅ Evento {event_id} deletado do banco')
                return True
            else:
                print(f'⚠️ Evento {event_id} não encontrado no banco')
                return False

        except Exception as e:
            conn.rollback()
            print(f'❌ Erro ao deletar evento: {e}')
            return False

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_user_by_number(number: str):
        conn = get_vector_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE phone_number = %s
                """,
                (number,),
            )

            row = cursor.fetchone()
            return row

        except Exception as e:
            print(f'❌ Erro ao buscar usuário: {e}')
            return None

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_doctor_for_id(calendar_id: str):
        conn = get_vector_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT name, doctor_number
                FROM doctor_rules
                WHERE calendar_id = %s
                """,
                (calendar_id,),
            )

            row = cursor.fetchone()
            return row

        except Exception as e:
            print(f'❌ Erro ao buscar responsável: {e}')
            return None

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def save_tokens(
        phone_number: str,
        message_id: str | None,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        model_name: str | None = None,
        provider: str | None = None,
    ):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO token_usage (
                    phone_number,
                    message_id,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    model_name,
                    provider
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    phone_number,
                    message_id,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    model_name,
                    provider,
                ),
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f'❌ Erro ao salvar tokens: {e}')

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_rag(query_embedding: list, categoria: str = None, limit: int = 3):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            if categoria:
                cursor.execute(
                    """
                    SELECT content, category,
                        embedding <=> %s::vector AS distance
                    FROM rag_embeddings
                    WHERE category = %s
                    ORDER BY distance
                    LIMIT %s
                    """,
                    (query_embedding, categoria, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT content, category,
                        embedding <=> %s::vector AS distance
                    FROM rag_embeddings
                    ORDER BY distance
                    LIMIT %s
                    """,
                    (query_embedding, limit)
                )

            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()