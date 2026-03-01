from src.agent.agents import Agent
from src.graph.states import NextAgent
from src.db.crud import PostgreSQL
from src.evo.client import EvolutionAPI
from src.graph.states import State
from src.graph.tools import Tools 
from src.prompts.context_providers import ContextProvider
from langchain_core.messages import AIMessage
from src.prompts.get_prompts import get_prompt
from dotenv import load_dotenv
import os

load_dotenv()

PROMPT_AGENDAMENTO = os.getenv("PROMPT_AGENDAMENTO")
PROMPT_RECEPCIONISTA = os.getenv("PROMPT_RECEPCIONISTA")
PROMPT_RAG = os.getenv('PROMPT_RAG')
PROMPT_ORQUESTRADOR = os.getenv('PROMPT_ORQUESTRADOR')


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

        PostgreSQL.create_user(phone_number=number)

        return state

    @staticmethod
    def node_save_message_user(state: State):
        messages = state['messages']
        number = state['number']

        if messages:
            ultima = messages[-1]
            conteudo = ultima.content
            message_payload = {'type': 'human', 'content': conteudo}
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
            PostgreSQL.save_message(session_id=number, sender='ai', agent_name=name_agent, message=message_payload)

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
        response = Tools.tool_node.invoke({'messages': [last_message]})

        return {'messages': [last_message] + response['messages']}

    @staticmethod
    def route_from_orquestrador(state: State) -> str:
        return state["next_agent"].next_agent

    @staticmethod
    def node_agent_recepcionista():
        return Agent(
            name="recepcionista",
            prompt=get_prompt(prompt_name=PROMPT_RECEPCIONISTA),
            llm=Tools.llm_with_tools_recepcionista,
            context_providers=[
                ContextProvider.context_calendario,
                ContextProvider.context_datetime,
                ContextProvider.context_user_number
            ]
        )

    @staticmethod
    def node_agent_rag():
        return Agent(
            name="rag",
            prompt=get_prompt(prompt_name=PROMPT_RAG),
            llm=Tools.llm_with_tools_rag,
            context_providers=[
                ContextProvider.context_datetime,
                ContextProvider.context_user_number
            ]
        )

    @staticmethod
    def node_agent_agendamento():
        return Agent(
            name="agendamento",
            prompt=get_prompt(prompt_name=PROMPT_AGENDAMENTO),
            llm=Tools.llm_with_tools_agendamento,
            context_providers=[
                ContextProvider.context_datetime,
                ContextProvider.context_user_number,
                ContextProvider.context_calendario
            ]
        )

    @staticmethod
    def node_agent_orquestrador():
        return Agent(
            name="orquestrador",
            prompt=get_prompt(prompt_name=PROMPT_ORQUESTRADOR),
            llm=Tools.llm_orquestrador,
            structured_schema=NextAgent
        )

    @staticmethod
    def node_chamar_humano(state: State):
        print(" =========== Encaminhando para Humano ===========")

        numero = state['number']
        motivo = state['next_agent'].reason

        try:
            PostgreSQL.update_require_human(phone_number=numero)
            
            evo = EvolutionAPI()
            evo.notify_human(phone_number=numero, reason=motivo)

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