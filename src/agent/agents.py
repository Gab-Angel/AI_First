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

class Agent:
    def __init__(
        self,
        name: str,
        prompt: str,
        llm,
        get_history,
        structured_schema=None
    ):
        self.name = name
        self.prompt = prompt
        self.llm = llm
        self.get_history = get_history
        self.structured_schema = structured_schema

    def __call__(self, state):
        print(f'🤖 Agente {self.name} pensando...')
        numero = state["number"]

        history = self.get_history(numero)
        history.extend(state["messages"])

        system_prompt = f"{self.prompt}"

        messages = [SystemMessage(content=system_prompt)] + history

        if self.structured_schema:
            llm = self.llm.with_structured_output(self.structured_schema)
            response = llm.invoke(messages)
            return {
                "next_agent": response,
                "agent_name": self.name
            }

        response = self.llm.invoke(messages)

        return {
            "messages": [response],
            "agent_name": self.name
        }
 