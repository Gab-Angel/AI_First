from langgraph.graph import END, StateGraph

from src.graph.nodes import Nodes
from src.graph.states import State

workflow = StateGraph(State)


workflow.add_node('verificar_user', lambda state: state)
workflow.add_node('verificar_cadastro', lambda state: state)
workflow.add_node('save_user', Nodes.node_save_user)
workflow.add_node('save_msg_human', Nodes.node_save_message_user)
workflow.add_node('sender_message', Nodes.node_sender_message)
workflow.add_node('save_msg_ai', Nodes.node_save_message_ai)
workflow.add_node('agente_recepcionista', Nodes.node_agent_recepcionista)
workflow.add_node('agente_orquestrador', Nodes.node_agent_orquestrador)
workflow.add_node('agente_rag', Nodes.node_agent_rag)
workflow.add_node('agente_agendamento', Nodes.node_agent_agendamento)
workflow.add_node('tool_node_recepcionista', Nodes.tool_node)
workflow.add_node('tool_node_orquestrador', Nodes.tool_node)
workflow.add_node('tool_node_rag', Nodes.tool_node)
workflow.add_node('tool_node_agendamento', Nodes.tool_node)
workflow.add_node('chamar_humano', Nodes.node_chamar_humano)

workflow.set_entry_point('verificar_user')

workflow.add_conditional_edges(
    'verificar_user',
    Nodes.node_verify_user,
    {'new': 'save_user', 'existent': 'save_msg_human'},
)

workflow.add_edge('save_user', 'save_msg_human')
workflow.add_edge('save_msg_human', 'verificar_cadastro')

workflow.add_conditional_edges(
    'verificar_cadastro',
    Nodes.node_verify_cadastro,
    {'recepcionista': 'agente_recepcionista', 'orquestrador': 'agente_orquestrador'},
)

workflow.add_conditional_edges(
    'agente_recepcionista',
    Nodes.should_continue,
    {'yes': 'tool_node_recepcionista', 'no': 'sender_message'},
)

workflow.add_conditional_edges(
    'agente_orquestrador',
    Nodes.route_from_orquestrador,
    {
        'rag': 'agente_rag', 
        'agendamento': 'agente_agendamento',
        'humano': 'chamar_humano'
     },
)

workflow.add_conditional_edges(
    'agente_rag',
    Nodes.should_continue,
    {'yes': 'tool_node_rag', 'no': 'sender_message'},
)

workflow.add_conditional_edges(
    'agente_agendamento',
    Nodes.should_continue,
    {'yes': 'tool_node_agendamento', 'no': 'sender_message'},
)

workflow.add_edge('tool_node_recepcionista', 'agente_recepcionista')
workflow.add_edge('tool_node_orquestrador', 'agente_orquestrador')
workflow.add_edge('tool_node_rag', 'agente_rag')
workflow.add_edge('tool_node_agendamento', 'agente_agendamento')

workflow.add_edge('chamar_humano', 'sender_message')
workflow.add_edge('sender_message', 'save_msg_ai')
workflow.add_edge('save_msg_ai', END)


graph = workflow.compile()