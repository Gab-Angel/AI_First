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
                SELECT cadastro_completo
                FROM users
                WHERE phone_number = %s
                """,
                (phone_number,),
            )
            result = cursor.fetchone()
            return result['cadastro_completo'] if result else False

        except Exception as e:
            print(f'❌ Erro ao buscar status cadastro: {e}')
            return False

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_user(phone_number: str, origem_contato: str = 'whatsapp'):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users (phone_number, origem_contato)
                VALUES (%s, %s)
                ON CONFLICT (phone_number) DO NOTHING
                """,
                (phone_number, origem_contato),
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
        nome_completo: str | None = None,
        cpf: str | None = None,
        convenio: str | None = None,
        cadastro_completo: str | None = None,
        observacoes: dict | None = None,
    ):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE users
                SET
                    nome_completo = COALESCE(%s, nome_completo),
                    cpf = COALESCE(%s, cpf),
                    convenio = COALESCE(%s, convenio),
                    cadastro_completo = COALESCE(%s, cadastro_completo),
                    observacoes = COALESCE(%s, observacoes)
                WHERE phone_number = %s
                """,
                (
                    nome_completo,
                    cpf,
                    convenio,
                    cadastro_completo,
                    json.dumps(observacoes) if observacoes else None,
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
            cadastro = True
            cursor.execute(
                """
                UPDATE users
                SET cadastro_completo = %s
                WHERE phone_number = %s
                """,
                (cadastro, phone_number),
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
            status = True
            cursor.execute(
                """
                UPDATE users
                SET require_human = %s
                WHERE phone_number = %s
                """,
                (status, phone_number),
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
                    FROM chat_ia
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
                            content='',  # tool_calls não têm content
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


    # ================================================================
    @staticmethod
    def get_file(categoria: str):

        try:
            conn = get_vector_conn()
            cursor = conn.cursor()

            query = """
                SELECT categoria, fileName, mediaType, caminho
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
    # ================================================================

    @staticmethod
    def save_calendar_event(
        session_id: str,
        event_id: str,
        summary: str,
        dr_responsavel: str,
        procedimento: str,
        start_time: str,
        end_time: str,
        description: str = ""
    ):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO calendar_events (session_id, event_id, summary, procedimento,  dr_responsavel, start_time, end_time, description)
                VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s AT TIME ZONE 'America/Sao_Paulo',
                %s AT TIME ZONE 'America/Sao_Paulo',
                %s
            )
            """,
                (session_id, event_id, summary, procedimento, dr_responsavel, start_time, end_time, description),
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
    def get_calendar_events(session_id: str):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT event_id, summary, start_time, end_time, description, created_at
                FROM calendar_events
                WHERE session_id = %s
                ORDER BY start_time ASC
            """,
                (session_id,),
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
    def delete_calendar_event(session_id: str, event_id: str):
        conn = get_vector_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                DELETE FROM calendar_events
                WHERE session_id = %s AND event_id = %s
            """,
                (session_id, event_id),
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

    # ================================================================
    @staticmethod
    def get_responsavel_event(event_id: str):
        conn = get_vector_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT dr_responsavel
                FROM calendar_events
                WHERE event_id = %s
            """,
                (event_id,),
            )

            row = cursor.fetchone()
            return row

        except Exception as e:
            print(f'❌ Erro ao buscar responsável: {e}')
            return None

        finally:
            cursor.close()
            conn.close()
    # ================================================================

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
                INSERT INTO agent_token_usage (
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
                    SELECT content, categoria, 
                        embedding <=> %s::vector AS distance
                    FROM rag_embeddings
                    WHERE categoria = %s
                    ORDER BY distance
                    LIMIT %s
                    """,
                    (query_embedding, categoria, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT content, categoria,
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


