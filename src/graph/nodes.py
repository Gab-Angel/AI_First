from src.agent.agents import agent_orquestrador, agent_agendamento, agent_rag, agent_recepcionista
from src.db.crud import PostgreSQL
from src.evo.client import EvolutionAPI
from src.graph.states import State
from src.graph.tools import Tools
from langchain_core.messages import AIMessage
from src.prompts.get_prompts import get_prompt
from dotenv import load_dotenv
import os

load_dotenv()

PROMPT_AGENDAMENTO = os.getenv("PROMPT_AGENDAMENTO")
PROMPT_RECEPCIONISTA = os.getenv("PROMPT_RECEPCIONISTA")
PROMPT_RAG = os.getenv('PROMPT_RAG')
PROMPT_ORQUESTRADOR = os.getenv('PROMPT_ORQUESTRADOR')

prompt_agendamento = get_prompt(prompt_name=PROMPT_AGENDAMENTO)
prompt_recepcionista = get_prompt(prompt_name=PROMPT_RECEPCIONISTA)
prompt_rag = get_prompt(prompt_name=PROMPT_RAG)
prompt_orquestrador = get_prompt(prompt_name=PROMPT_ORQUESTRADOR)

evo = EvolutionAPI()

class Nodes:
    
    @staticmethod
    def node_verify_user(state: State):
        number = state['number']

        exist = PostgreSQL.verify_user(phone_number=number)

        if exist:
            print(f'✅ Usuário {number} já existe')
            return 'existent'
        else:
            print(f'🆕 Novo Usuário {number}')
            return 'new'
        
    @staticmethod
    def node_verify_cadastro(state: State):
        number = state['number']
    
        cadastro_completo = PostgreSQL.verify_cadastro(phone_number=number)
        
        if cadastro_completo:
            print(f'✅ Cadastro completo - {number}')
            return 'orquestrador'
        else:
            print(f'📝 Cadastro incompleto - {number}')
            return 'recepcionista'
    
    @staticmethod
    def node_save_user(state: State):
        number = state['number']

        PostgreSQL.create_user(
            phone_number=number
        )

        return state

    @staticmethod
    def node_save_message_user(state: State):
        messages = state['messages']
        number = state['number']

        if messages:
            ultima = messages[-1]
            conteudo = ultima.content

            message_payload = {'type': 'user', 'content': conteudo}

            PostgreSQL.save_message(session_id=number, sender='user', message=message_payload)

        return state
    
    @staticmethod
    def node_save_message_ai(state: State):

        message = state['messages']
        number = state['number']
        name_agent = state['agent_name']

        if message:
            ultima = message[-1]
            conteudo = ultima.content

            message_payload = {'type': 'ai', 'content': conteudo}

            PostgreSQL.save_message(session_id=number, sender='ai', agent_name=name_agent ,message=message_payload)

        return state

    @staticmethod
    def node_sender_message(state):
        messages = state['messages']
        number = state['number']

        last_message = messages[-1]
        text = last_message.content
        evo.sender_text(number=number, text=text)

        return state

    @staticmethod
    def should_continue(state: State) -> str:
        last_message = state['messages'][-1]

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            print('🔍 Decisão: Chamar ferramentas.')
            return 'yes'
        else:
            print('✅ Decisão: Finalizar e responder.')
            return 'no'
        
    @staticmethod
    def tool_node(state: State):
        print('🛠️ Executando ferramentas...')
        
        last_message = state['messages'][-1]
        number = state['number']

        response = Tools.tool_node.invoke({'messages': [last_message]})

        # Lista de tools que precisam ser salvas para dar contexto à IA
        tools_to_save = [
            tc for tc in last_message.tool_calls 
            if tc['name'] in ['listar_doutores_disponiveis', 'buscar_detalhes_doutor']
        ]
        
        if tools_to_save:
            # ✅ Salva a tool_call ANTES
            tool_calls_payload = {
                'type': 'tool_calls',
                'content': last_message.tool_calls
            }
            PostgreSQL.save_message(session_id=number, message=tool_calls_payload)
            
            # ✅ Depois salva o resultado
            for i, tool_msg in enumerate(response['messages']):
                tool_call = last_message.tool_calls[i]
                
                if tool_call['name'] in ['listar_doutores_disponiveis', 'buscar_detalhes_doutor']:
                    tool_result_payload = {
                        'type': 'tool',
                        'content': tool_msg.content,
                        'tool_call_id': tool_msg.tool_call_id
                    }
                    PostgreSQL.save_message(session_id=number, message=tool_result_payload)

        return {'messages': [last_message] + response['messages']}

    @staticmethod
    def node_agent_orquestrador(state: State):
        return agent_orquestrador(
            state=state,
            prompt_ia=prompt_orquestrador,
            get_history=PostgreSQL.get_historico,
        )

    @staticmethod
    def route_from_orquestrador(state: State) -> str:
        return state["next_agent"].next_agent

    @staticmethod
    def node_agent_recepcionista(state: State):
        return agent_recepcionista(
            state=state,
            prompt_ia=prompt_recepcionista,
            llm_model=Tools.llm_with_tools_recepcionista,
            get_history=PostgreSQL.get_historico,
        )
    
    @staticmethod
    def node_agent_rag(state: State):
        return agent_rag(
            state=state,
            prompt_ia=prompt_rag,
            llm_model=Tools.llm_with_tools_rag,
            get_history=PostgreSQL.get_historico,
        )
    
    @staticmethod
    def node_agent_agendamento(state: State):
        return agent_agendamento(
            state=state,
            prompt_ia=prompt_agendamento,
            llm_model=Tools.llm_with_tools_agendamento,
            get_history=PostgreSQL.get_historico,
        )
    
    @staticmethod
    def node_chamar_humano(state: State):
        print(" =========== Encaminhando para Humano ===========")

        numero = state['number']
        motivo = state['next_agent'].reason

        try:
            PostgreSQL.update_require_human(phone_number=numero)

            EvolutionAPI.notify_human(
                phone_number=numero,
                reason=motivo
            )

            return {'messages': [
                AIMessage(
                    content=(
                            "Estou te transferindo para um humano 👩‍⚕️👨‍⚕️\n"
                            "Assim que possível, alguém irá continuar o atendimento."
                            )
                        )
            ]}
        

        except Exception as e:
            print(f"🔍 DEBUG - Erro capturado: {e}")
            return {'messages': [AIMessage(content="Houve um erro ao encaminhar para um humano. Tente novamente em instantes.")]}
        