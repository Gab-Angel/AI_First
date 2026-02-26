from langchain.tools import tool
from dotenv import load_dotenv
import os
import json
from langgraph.prebuilt import ToolNode
from src.evo.client import EvolutionAPI
from src.agent.agents import llm
from src.google_calendar.client_calendar import GoogleCalendarClient
from src.db.crud import PostgreSQL
from src.db.connection import get_vector_conn
from src.scheduler.schedulers import create_scheduler_message, delete_scheduler_message
from openai import OpenAI

load_dotenv()

client = OpenAI()

calendar_client = GoogleCalendarClient()


class Tools:
    @tool(description="""
    Salva informações do paciente no cadastro.
    
    Args:
        phone_number: Número do paciente (obrigatório)
        nome_completo: Nome completo fornecido
        cpf: CPF do paciente
        convenio: Convênio médico
        observacoes: Informações adicionais
    
    Returns:
        Confirmação de atualização
""")
    def atualizar_cadastro(
        phone_number: str,
        nome_completo: str | None = None,
        cpf: str | None = None,
        convenio: str | None = None,
        observacoes: dict | None = None,
    ) -> str:
        print("Ferramenta: =========== Atualizar Cadastro ===========")
        
        try:
            PostgreSQL.update_user(
                phone_number=phone_number,
                nome_completo=nome_completo,
                cpf=cpf,
                convenio=convenio,
                observacoes=observacoes,
            )
            return "Cadastro atualizado com sucesso."
        
        except Exception as e:
            return f"Erro ao atualizar cadastro: {str(e)}"

    @tool(description="""
        Finaliza o cadastro do paciente, marcando como completo.
        
        Use APENAS quando tiver coletado TODAS as informações obrigatórias:
        - Nome completo
        - CPF
        - Convênio
        
        Args:
            phone_number: Número do paciente (obrigatório)
        
        Returns:
            Confirmação de finalização
    """)
    def finalizar_cadastro(phone_number: str) -> str:
        print("Ferramenta: =========== Finalizar Cadastro ===========")
    
        try:
            PostgreSQL.finally_user(phone_number=phone_number)

            return "Cadastro finalizado. Paciente pode agendar consultas."
        
        except Exception as e:
            print(f"🔍 DEBUG - Erro capturado: {e}")
            return f"Erro ao finalizar cadastro: {str(e)}"

    @tool(description="""
        Busca informações vetoriais na base de conhecimento do consultório.
        
        QUANDO USAR:
        - Paciente pergunta sobre consultório, doutores, história, localização
        - Paciente pergunta sobre serviços, procedimentos, preços, tratamentos
        - Qualquer dúvida que NÃO seja agendamento/cancelamento/reagendamento
        
        IMPORTANTE:
        - Use SEMPRE antes de responder dúvidas sobre o consultório
        - Não invente respostas: se o RAG retornar vazio, diga "Não tenho essa informação"
        - A resposta do RAG é a fonte oficial de verdade
        
        Args:
            query: Pergunta exata do paciente ou termo-chave (ex: "quanto custa clareamento")
            categoria: Filtro de busca (obrigatório):
                - "sobre": consultório, equipe, história, localização, contato
                - "servicos": procedimentos, tratamentos, valores, formas de pagamento
        
        Returns:
            Trechos relevantes da base de conhecimento ou mensagem de não encontrado
        """)
    def buscar_rag(query: str, categoria: str = None) -> str:

        print("Ferramenta: =========== Buscar no RAG ===========")
        print(f"QUERY:  === {query} ==="
              f"CATEGORIA: === {categoria} ==="
              )
        # Gera embedding
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = response.data[0].embedding
        
        # Busca no BD
        results = PostgreSQL.get_rag(query_embedding=query_embedding, categoria=categoria)
        
        if not results:
            return "Nenhuma informação encontrada."
        
        # Formata resposta
        contexto = "\n\n".join([
            f"[{r['categoria']}] {r['content']}"
            for r in results
        ])
        
        return f"Informações encontradas:\n\n{contexto}"
    
    @tool(description="""
        Envia arquivo institucional ao paciente.
        
        Tipos: cardapio, localizacao, convenios, etc
        """)
    def enviar_arquivo(numero: str, tipo: str) -> str:
        
        file_info = PostgreSQL.get_file(categoria=tipo)
        
        if not file_info:
            return f"Arquivo '{tipo}' não encontrado"
        
        # Envia
        evo = EvolutionAPI()
        evo.sender_file(
            numero=numero,
            media_type=file_info['mediaType'],
            file_name=file_info['fileName'],
            media=file_info['path']
        )
        
        return f"Arquivo '{file_info['fileName']}' enviado"

    @tool(description=
          """
        Lista doutores disponíveis para um procedimento específico.
        
        QUANDO USAR: Logo após paciente informar qual procedimento deseja.
        
        Args:
            procedimento: Nome do procedimento (obrigatório) - ex: "limpeza", "canal", "clareamento"
            convenio: Convênio do paciente (opcional) - ex: "unimed", "bradesco", "particular"
        
        Returns:
            JSON com lista de doutores elegíveis (id e nome apenas)
        
        Exemplo de retorno:
        [
            {"id": "uuid-123", "nome": "Doutor A"},
            {"id": "uuid-456", "nome": "Doutor B"}
        ]
    """)
    def listar_doutores_disponiveis(procedimento: str, convenio: str = None) -> str:
        print("Ferramenta: =========== Listar Doutores Disponíveis ===========")
        print(f"Procedimento: {procedimento}")
        print(f"Convênio: {convenio or 'Não informado'}")
        
        try:
            conn = get_vector_conn()
            cursor = conn.cursor()
            
            query = """
                SELECT id, name
                FROM doctor_rules
                WHERE active = true
                  AND EXISTS (
                    SELECT 1 FROM jsonb_array_elements(procedures) AS p
                    WHERE lower(p->>'nome') = lower(%s)
                  )
            """
            
            params = [procedimento]
            
            if convenio:
                query += " AND insurances @> %s::jsonb"
                params.append(json.dumps([convenio.lower()]))
            
            cursor.execute(query, params)
            doutores = cursor.fetchall()
            
            if not doutores:
                return "Nenhum doutor disponível para este procedimento/convênio."
            
            resultado = [
                {"id": str(dr['id']), "nome": dr['name']}
                for dr in doutores
            ]
            
            print(f"✅ Encontrados {len(resultado)} doutor(es)")
            return json.dumps(resultado, ensure_ascii=False)
            
        except Exception as e:
            print(f"❌ Erro ao listar doutores: {e}")
            return f"Erro ao buscar doutores: {str(e)}"
        
        finally:
            cursor.close()
            conn.close()
   
    @tool(description="""
        Busca detalhes completos de um doutor específico após escolha do paciente.
        
        QUANDO USAR: Após paciente escolher o doutor da lista.
        
        Args:
            doutor_id: UUID do doutor escolhido (obrigatório)
        
        Returns:
            JSON com todas as informações do doutor:
            - id, nome, calendar_id
            - procedimentos que atende
            - duração padrão das consultas
            - dias da semana que trabalha
            - horário de início e fim
            - convênios aceitos
        
        Exemplo de retorno:
        {
            "id": "uuid-123",
            "nome": "Rosevânia",
            "calendar_id": "primary@gmail.com",
            "procedimentos": ["limpeza", "canal"],
            "duracao_minutos": 60,
            "dias_trabalho": [1,2,3,4,5],
            "horarios": {
                "manha": {"inicio": "08:00", "fim": "12:00"},
                "tarde": {"inicio": "14:00", "fim": "18:00"}
            },
            "convenios": ["unimed", "bradesco"]
        }
    """)
    def buscar_detalhes_doutor(doutor_id: str) -> str:
        print("Ferramenta: =========== Buscar Detalhes do Doutor ===========")
        print(f"Doutor ID: {doutor_id}")
        
        try:
            conn = get_vector_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id, name, calendar_id, procedures, duration,
                    available_weekdays, working_hours, 
                    insurances, restrictions
                FROM doctor_rules
                WHERE id = %s AND active = true
            """, (doutor_id,))
            
            doutor = cursor.fetchone()
            
            if not doutor:
                return f"Doutor com ID {doutor_id} não encontrado ou inativo."
            
            # Formata resultado
            resultado = {
                "id": str(doutor['id']),
                "nome": doutor['name'],
                "calendar_id": doutor['calendar_id'],
                "procedimentos": doutor['procedures'],
                "duracao_minutos": doutor['duration'],
                "dias_trabalho": doutor['available_weekdays'],
                "horarios": doutor['working_hours'],
                "convenios": doutor['insurances'],
                "restricoes": doutor.get('restrictions')
            }
            
            print(f"✅ Detalhes do doutor {doutor['name']} carregados")
            return json.dumps(resultado, ensure_ascii=False)
            
        except Exception as e:
            print(f"❌ Erro ao buscar detalhes do doutor: {e}")
            return f"Erro ao buscar detalhes: {str(e)}"
        
        finally:
            cursor.close()
            conn.close()
    
    @tool(description="""
        Verifica se um horário específico está livre ou ocupado na agenda.
        
        QUANDO USAR: Após paciente informar data/hora desejada e ANTES de agendar.
        
        IMPORTANTE: 
        - Se retornar "livre" → agende imediatamente com agendar_consulta
        - Se retornar "ocupado" → pergunte outro horário ao paciente
        
        Args:
            number: Número do paciente (obrigatório)
            calendar_id: ID do calendário do doutor escolhido (obrigatório)
            data_inicio: Data/hora início ISO 8601 - ex: "2026-01-17T14:00:00-03:00"
            data_fim: Data/hora fim ISO 8601 - ex: "2026-01-17T15:00:00-03:00"
        
        Returns:
            "Agenda livre" OU lista de eventos ocupados
    """)
    def verificar_agenda(
        number: str,
        data_inicio: str,
        data_fim: str,
        calendar_id: str
    ) -> str:
        
        print("Ferramenta: =========== Verificar Agenda ===========")
        try:
            eventos = calendar_client.verificar(
                data_inicio=data_inicio,
                data_fim=data_fim,
                calendar_id=calendar_id
            )
            
            if not eventos:
                return f"Agenda completamente livre entre {data_inicio} e {data_fim}"
            
            resultado = f"Eventos ocupados ({len(eventos)}):\n"
            for evento in eventos:
                resultado += f"- {evento['summary']}: {evento['start']} até {evento['end']}\n"
            
            return resultado
            
        except Exception as e:
            return f"Erro ao verificar agenda: {str(e)}"
    
    @tool(description="""
        Cria agendamento no Google Calendar após confirmar disponibilidade.
        
        QUANDO USAR: Imediatamente após verificar_agenda retornar "livre".
        NÃO peça confirmação novamente - execute direto.
        
        Args:
            number: Número do paciente (obrigatório)
            summary: Título - use "Consulta Odontológica" (obrigatório)
            calendar_id: ID do calendário do doutor (obrigatório)
            procedimento: Procedimento escolhido pelo paciente (obrigatório)
            data_inicio: Data/hora início ISO 8601 (obrigatório)
            data_fim: Data/hora fim ISO 8601 (obrigatório)
            description: Observações importantes (obrigatório)
        
        Returns:
            Confirmação com detalhes do agendamento
    """)
    def agendar_consulta(
        number: str,
        summary: str,
        calendar_id: str,
        procedimento: str,
        data_inicio: str,
        data_fim: str,
        description: str,
    ) -> str:

        print("Ferramenta: =========== Agendar Consulta ===========")
        try:
            # Cria no Google Calendar
            evento = calendar_client.adicionar(
                summary= f"Consulta com {number}",
                start_time=data_inicio,
                end_time=data_fim,
                calendar_id=calendar_id,
                description=description
            )

            doutor = PostgreSQL.get_doctor_for_id(calendar_id=calendar_id)


            PostgreSQL.save_calendar_event(
                session_id=number,
                event_id=evento['id'],
                summary=evento['summary'],
                procedure=procedimento,
                dr_responsible=doutor['name'],
                start_time=evento['start'],
                end_time=evento['end'],
                description=description
            )

            evo = EvolutionAPI()
            evo.notificar_admin_agendamento(
                paciente_numero=number,
                procedimento=procedimento,
                descricao=description,
                doctor_number=doutor['doctor_number'],
                data_inicio=evento['start'],
                data_fim=evento['end']
            )
            
            message_id_scheduler = evento['id']

            create_scheduler = create_scheduler_message(
                event_id_scheduler=message_id_scheduler,
                numero=number,
                schedule_time=data_inicio
            )

            print(create_scheduler)

            return (
                f"✅ Consulta agendada com sucesso!\n"
                f"Título: {evento['summary']}\n"
                f"Início: {evento['start']}\n"
                f"Fim: {evento['end']}\n"
                f"ID: {evento['id']}"
            )
            
        except Exception as e:
            print(e)
            return f"Erro ao agendar consulta: {str(e)}"
    
    @tool(description="""
        Cancela consulta agendada do paciente.
        
        QUANDO USAR: 
        - No cancelamento: após paciente fornecer data + hora
        - No reagendamento: após paciente fornecer data/hora DA CONSULTA ANTIGA
        
        Args:
            number: Número do paciente (obrigatório)
            calendar_id: ID do calendário onde está agendada (obrigatório)
            data: Data no formato YYYY-MM-DD - ex: "2026-01-17" (obrigatório)
            hora: Hora no formato HH:MM - ex: "14:00" (obrigatório para evitar erros)
        
        Returns:
            Confirmação de cancelamento
    """)
    def cancelar_consulta(
        number: str,
        calendar_id: str,
        data: str,
        hora: str = None
    ) -> str:
        print(f"[CANCELAR] number={number}, data={data}, hora={hora}")
        print("Ferramenta: =========== Cancelar Consulta ===========")
        try:
            eventos = PostgreSQL.get_calendar_events(user_number=number)
            print(f"[CANCELAR] Total eventos: {len(eventos)}")
            
            # Filtra por data (converte datetime para string)
            eventos_na_data = [
                e for e in eventos 
                if e['start_time'].strftime('%Y-%m-%d') == data
            ]
            
            print(f"[CANCELAR] Eventos na data: {len(eventos_na_data)}")
            
            if not eventos_na_data:
                return f"Nenhuma consulta encontrada para {data}"
            
            # Se hora foi fornecida, filtra também por hora
            if hora:
                eventos_filtrados = [
                    e for e in eventos_na_data
                    if e['start_time'].strftime('%H:%M') == hora
                ]
                
                if not eventos_filtrados:
                    return f"Nenhuma consulta encontrada para {data} às {hora}"
                
                evento = eventos_filtrados[0]
            else:
                if len(eventos_na_data) == 1:
                    evento = eventos_na_data[0]
                else:
                    lista = "Encontrei múltiplas consultas nesta data:\n"
                    for e in eventos_na_data:
                        horario = e['start_time'].strftime('%H:%M')
                        lista += f"- {e['summary']} às {horario}\n"
                    lista += "\nEspecifique o horário."
                    return lista
            
            # Deleta
            calendar_client.deletar(event_id=evento['event_id'], calendar_id=calendar_id)
            PostgreSQL.delete_calendar_event(user_number=number, event_id=evento['event_id'])
            
            delete_scheduler = delete_scheduler_message(
                event_id_scheduler=evento['event_id']
            )

            print(delete_scheduler)

            return (
                f"✅ Consulta cancelada com sucesso!\n"
                f"Título: {evento['summary']}\n"
                f"Era agendada para: {evento['start_time'].strftime('%Y-%m-%d %H:%M')}"
            )
            
        except Exception as e:
            return f"Erro ao cancelar consulta: {str(e)}"


    tools_agendamento = [
        listar_doutores_disponiveis,
        buscar_detalhes_doutor,
        verificar_agenda,
        agendar_consulta,
        cancelar_consulta
    ]

    tools_recepcionista = [
        atualizar_cadastro,
        finalizar_cadastro
    ]
    
    tools_rag = [
        buscar_rag,
        enviar_arquivo
    ]

    tools = tools_recepcionista + tools_agendamento + tools_rag 

    tool_node = ToolNode(tools)

    llm_with_tools_recepcionista = llm.bind_tools(tools_recepcionista)
    llm_with_tools_agendamento = llm.bind_tools(tools_agendamento)
    llm_with_tools_rag = llm.bind_tools(tools_rag)
    llm_orquestrador = llm
