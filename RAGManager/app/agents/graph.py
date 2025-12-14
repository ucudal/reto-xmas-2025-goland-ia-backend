"""Main graph definition and construction for the LangGraph agent."""

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    agent_host,
    context_builder,
    fallback,
    guard_inicial,
    guard_final,
    parafraseo,
    retriever,
)
from app.agents.state import AgentState
from app.agents.routing import route_after_guard, route_after_guard_final

def create_agent_graph() -> StateGraph:
    """
    Create and configure the LangGraph agent graph.

    The graph implements the following flow:
    1. START -> agent_host (Nodo 1)
    2. agent_host -> guard_inicial (Nodo 2)
    3. guard_inicial -> [conditional] -> fallback (if malicious) or parafraseo (if valid)
    4. parafraseo -> retriever (Nodo 5)
    5. retriever -> context_builder (Nodo 6)
    6. context_builder -> guard_final (Nodo 7)
    7. guard_final -> [conditional] -> fallback (if risky/PII detected) or END (if valid)
    8. fallback -> END

    Returns:
        Configured StateGraph instance ready for execution
    """
    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent_host", agent_host)
    workflow.add_node("guard_inicial", guard_inicial)
    workflow.add_node("guard_final", guard_final)
    workflow.add_node("fallback", fallback)
    workflow.add_node("parafraseo", parafraseo)
    workflow.add_node("retriever", retriever)
    workflow.add_node("context_builder", context_builder)

    # Define edges
    # Start -> agent_host
    workflow.add_edge(START, "agent_host")

    # agent_host -> guard_inicial
    workflow.add_edge("agent_host", "guard_inicial")

    # guard_inicial -> conditional routing (first guard check)
    workflow.add_conditional_edges(
        "guard_inicial",
        route_after_guard,
        {
            "malicious": "fallback",  # go to fallback if malicious
            "continue": "parafraseo",  # Continue to parafraseo if valid
        },
    )

    # parafraseo -> retriever
    workflow.add_edge("parafraseo", "retriever")

    # retriever -> context_builder
    workflow.add_edge("retriever", "context_builder")

    # context_builder -> guard_final
    workflow.add_edge("context_builder", "guard_final")

    # guard_final -> conditional routing (second guard check for PII)
    workflow.add_conditional_edges(
        "guard_final",
        route_after_guard_final,
        {
            "risky": "fallback",  # go to fallback if risky (PII detected)
            "continue": END,  # if there's no error ends
        },
    )
    
    # fallback -> END
    workflow.add_edge("fallback", END)
    # Compile the graph
    return workflow.compile()
