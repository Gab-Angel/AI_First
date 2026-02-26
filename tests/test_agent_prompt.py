import pytest
from langchain_core.messages import SystemMessage, HumanMessage

from src.agent.agents import Agent


# -----------------------------
# FAKES (mocks simples)
# -----------------------------

class FakeLLM:
    def __init__(self):
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return HumanMessage(content="resposta fake")


def fake_get_history(number):
    return [HumanMessage(content="mensagem antiga")]


def fake_context_1(state):
    return "CONTEXTO 1"


def fake_context_2(state):
    return "CONTEXTO 2"


# -----------------------------
# TESTE
# -----------------------------

def test_system_prompt_is_built_correctly():
    fake_llm = FakeLLM()

    agent = Agent(
        name="teste",
        prompt="PROMPT BASE",
        llm=fake_llm,
        get_history=fake_get_history,
        context_providers=[fake_context_1, fake_context_2],
    )

    state = {
        "number": "123",
        "messages": [HumanMessage(content="mensagem nova")]
    }

    agent(state)

    # Captura o SystemMessage enviado ao LLM
    sent_messages = fake_llm.last_messages
    system_message = sent_messages[0]

    assert isinstance(system_message, SystemMessage)

    system_content = system_message.content

    # Verifica se tudo foi incluído
    assert "PROMPT BASE" in system_content
    assert "CONTEXTO 1" in system_content
    assert "CONTEXTO 2" in system_content

    # Verifica histórico completo
    assert len(sent_messages) == 3
    print(f'\n\n {system_content}')  # system + antiga + nova