"""Main graph definition and construction for the LangGraph agent."""

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    agent_host,
    context_builder,
    fallback_final,
    fallback_inicial,
    generator,
    guard_final,
    guard_inicial,
    parafraseo,
    retriever,
)
from app.agents.routing import route_after_fallback_final, route_after_guard, route_after_guard_final
from app.agents.state import AgentState


def create_agent_graph() -> StateGraph:
    """
    Create and configure the LangGraph agent graph.

    The graph implements the following flow:
    1. START -> agent_host (Nodo 1)
    2. agent_host -> guard_inicial (Nodo 2) - Jailbreak detection
    3. guard_inicial -> [conditional] -> fallback_inicial (Nodo 3) or parafraseo
    4. fallback_inicial -> parafraseo (Nodo 4)
    5. parafraseo -> retriever (Nodo 5)
    6. retriever -> context_builder (Nodo 6)
    7. context_builder -> generator (Nodo 7)
    8. generator -> guard_final - PII detection
    9. guard_final -> [conditional] -> fallback_final (Nodo 8) or END
    10. fallback_final -> [conditional] -> END (with final_response) or END (with error)

    Returns:
        Configured StateGraph instance ready for execution
    """
    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent_host", agent_host)
    workflow.add_node("guard_inicial", guard_inicial)
    workflow.add_node("fallback_inicial", fallback_inicial)
    workflow.add_node("parafraseo", parafraseo)
    workflow.add_node("retriever", retriever)
    workflow.add_node("context_builder", context_builder)
    workflow.add_node("generator", generator)
    workflow.add_node("guard_final", guard_final)
    workflow.add_node("fallback_final", fallback_final)

    # Define edges
    # Start -> agent_host
    workflow.add_edge(START, "agent_host")

    # agent_host -> guard_inicial
    workflow.add_edge("agent_host", "guard_inicial")

    # guard_inicial -> conditional routing
    workflow.add_conditional_edges(
        "guard_inicial",
        route_after_guard,
        {
            "malicious": "fallback_inicial",  # go to fallback_inicial if malicious
            "continue": "parafraseo",  # Continue to parafraseo if valid
        },
    )

    # parafraseo -> retriever
    workflow.add_edge("parafraseo", "retriever")

    # retriever -> context_builder
    workflow.add_edge("retriever", "context_builder")

    # context_builder -> generator
    # Note: Primary LLM is called within context_builder node
    workflow.add_edge("context_builder", "generator")

    # generator -> guard_final
    workflow.add_edge("generator", "guard_final")

    # guard_final -> conditional routing
    workflow.add_conditional_edges(
        "guard_final",
        route_after_guard_final,
        {
            "risky": "fallback_final",  # go to fallback_final if PII detected
            "continue": END,  # if there's no error ends
        },
    )

    # Compile the graph
    return workflow.compile()
