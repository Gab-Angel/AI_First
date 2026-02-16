import os 
from datetime import datetime, timedelta
from dotenv import load_dotenv
# from langchain_openai import ChatOpenAI
from langchain_cerebras import ChatCerebras
from langchain_core.messages import SystemMessage
from src.graph.states import NextAgent

load_dotenv()

# horário atual
DIAS_PT = {
    "Monday": "segunda-feira",
    "Tuesday": "terça-feira",
    "Wednesday": "quarta-feira",
    "Thursday": "quinta-feira",
    "Friday": "sexta-feira",
    "Saturday": "sábado",
    "Sunday": "domingo",
}

now_dt = datetime.now()
day_en = now_dt.strftime("%A")
day_pt = DIAS_PT.get(day_en, day_en)

now = now_dt.strftime("%Y-%m-%d %H:%M:%S") + f" | {day_pt}"

def gerar_calendario_4_semanas():
    """Gera calendário das próximas 2 semanas"""
    hoje = datetime.now()
    dias_semana = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
    
    calendario = []
    for i in range(31):
        data = hoje + timedelta(days=i)
        dia_semana = dias_semana[data.weekday()]
        calendario.append(f"{data.strftime('%d/%m')} ({dia_semana})")
    
    return " | ".join(calendario)

# No system_prompt:
calendario_ref = gerar_calendario_4_semanas()


llm = ChatCerebras(
    api_key=os.getenv('CEREBRAS_API_KEY'),
    model=os.getenv('CEREBRAS_MODEL'),
    temperature=0
)


# MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4.1")
# llm = ChatOpenAI(
#     api_key=os.getenv('OPENAI_API_KEY'),
#     model=MODEL_NAME,
#     temperature=0,
# )

def agent_recepcionista(state, prompt_ia: str, llm_model, get_history):
    numero = state['number']

    # Recupera histórico com função injetada (agora síncrona)
    mensagens_historico = get_history(numero)

    # Junta com mensagens do state (mensagem atual)
    mensagens_historico.extend(state['messages'])

    print('🤖 Agente Recepcionista pensando...')

    system_prompt = (
        f'{prompt_ia}\n\n'
        f'DATA/HORA ATUAL: {now}\n'
        f'IMPORTANTE: O número do usuário é {numero}. '
    )

    messages = [SystemMessage(content=system_prompt)] + mensagens_historico

    # Chamada do modelo
    response = llm_model.invoke(messages)

    return {
        'messages': [response],
        'agent_name': 'recepcionista'
        }


def agent_orquestrador(state, prompt_ia: str, get_history):
    numero = state['number']

    # Recupera histórico com função injetada (agora síncrona)
    mensagens_historico = get_history(numero)

    # Junta com mensagens do state (mensagem atual)
    mensagens_historico.extend(state['messages'])

    print('🤖 Agente Orquestrador pensando...')

    system_prompt = (
        f'{prompt_ia}\n\n'
        f'DATA/HORA ATUAL: {now}\n'
        f'IMPORTANTE: O número do usuário é {numero}. '
    )

    messages = [SystemMessage(content=system_prompt)] + mensagens_historico

    structured_llm = llm.with_structured_output(NextAgent)
    # Chamada do modelo
    response = structured_llm.invoke(messages)

    return {
            "next_agent": response,
            "agent_name": 'orquestrador'
        }



def agent_rag(state, prompt_ia: str, llm_model, get_history):
    numero = state['number']

    mensagens_historico = get_history(numero)

    mensagens_historico.extend(state['messages'])

    print('🤖 Agente Rag pensando...')

    system_prompt = (
        f'{prompt_ia}\n\n'
        f'DATA/HORA ATUAL: {now}\n'
        f'IMPORTANTE: O número do usuário é {numero}. '
    )

    messages = [SystemMessage(content=system_prompt)] + mensagens_historico

    response = llm_model.invoke(messages)

    return {
        'messages': [response],
        'agent_name': 'rag'
        }


def agent_agendamento(state, prompt_ia: str, llm_model, get_history):
    numero = state['number']

    # Recupera histórico com função injetada (agora síncrona)
    mensagens_historico = get_history(numero)

    # Junta com mensagens do state (mensagem atual)
    mensagens_historico.extend(state['messages'])

    print('🤖 Agente Agendamento pensando...')

    system_prompt = (
        f'{prompt_ia}\n\n'
        f'DATA/HORA ATUAL: {now}\n'
        f'CALENDÁRIO de 31 dias: {calendario_ref}\n'
        f'IMPORTANTE: Use o calendário acima para identificar dias da semana.\n'
        f'IMPORTANTE: O número do usuário é {numero}. '
        f'Use sempre este número ao chamar ferramentas.'
    )

    messages = [SystemMessage(content=system_prompt)] + mensagens_historico

    # Chamada do modelo
    response = llm_model.invoke(messages)

    return {
        'messages': [response],
        'agent_name': 'agendamento'
        }

 