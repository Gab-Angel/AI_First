import os 
from dotenv import load_dotenv
from langchain_cerebras import ChatCerebras
from langchain_core.messages import SystemMessage, ToolMessage
from typing import List, Optional

load_dotenv()

MAX_MESSAGES = 20

llm = ChatCerebras(
    api_key=os.getenv('CEREBRAS_API_KEY'),
    model=os.getenv('CEREBRAS_MODEL'),
    temperature=0
)

# llm = ChatOpenAI(
#     api_key=os.getenv('OPENAI_API_KEY'),
#     model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
#     temperature=0,
# )

class Agent:
    def __init__(
        self,
        name: str,
        prompt: str,
        llm,
        structured_schema: Optional[object] = None,
        context_providers: Optional[List] = None,
    ):
        self.name = name
        self.prompt = prompt
        self.llm = llm
        self.structured_schema = structured_schema
        self.context_providers = context_providers or []

    def __call__(self, state):
        print(f'🤖 Agente {self.name} pensando...')

        context_parts = [
            provider(state)
            for provider in self.context_providers
        ]

        context_text = "\n".join(context_parts)

        system_prompt = (
            f"{self.prompt}\n\n"
            f"{context_text}"
        )

        # 1. Limita o histórico a 20 mensagens
        message_history = state['messages'][-MAX_MESSAGES:]

        # 2. Garante que não começa com ToolMessage sem tool_call pareado
        while message_history and isinstance(message_history[0], ToolMessage):
            message_history = message_history[1:]

        messages = [SystemMessage(content=system_prompt)] + message_history

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