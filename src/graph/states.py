from langchain_core.messages import AnyMessage
from typing import Literal, Optional
from pydantic import BaseModel
from langgraph.graph import add_messages
from typing_extensions import Annotated, TypedDict

class NextAgent(BaseModel):
    next_agent: Literal['rag', 'agendamento', 'humano']
    reason: Optional[str] = None

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    number: str
    next_agent: Optional[NextAgent] = None
    agent_name: Optional[str] = None