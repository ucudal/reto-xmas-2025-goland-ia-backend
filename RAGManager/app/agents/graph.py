"""Main graph definition and construction for the LangGraph agent."""

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    agent_host,
    context_builder,
    fallback_final,
    fallback_inicial,
    generator,
    guard,
    parafraseo,
    retriever,
)
from app.agents.routing import route_after_fallback_final, route_after_guard
from app.agents.state import AgentState


def create_agent_graph() -> StateGraph:
    """
    Create and configure the LangGraph agent graph.

    The graph implements the following flow:
    1. START -> agent_host (Nodo 1)
    2. agent_host -> guard (Nodo 2)
    3. guard -> [conditional] -> fallback_inicial (Nodo 3) or END
    4. fallback_inicial -> parafraseo (Nodo 4)
    5. parafraseo -> retriever (Nodo 5)
    6. retriever -> context_builder (Nodo 6)
    7. context_builder -> generator (Nodo 7)
    8. generator -> fallback_final (Nodo 8)
    9. fallback_final -> [conditional] -> END (with final_response) or END (with error)

    Returns:
        Configured StateGraph instance ready for execution
    """
    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent_host", agent_host)
    workflow.add_node("guard", guard)
    workflow.add_node("fallback_inicial", fallback_inicial)
    workflow.add_node("parafraseo", parafraseo)
    workflow.add_node("retriever", retriever)
    workflow.add_node("context_builder", context_builder)
    workflow.add_node("generator", generator)
    workflow.add_node("fallback_final", fallback_final)

    # Define edges
    # Start -> agent_host
    workflow.add_edge(START, "agent_host")

    # agent_host -> guard
    workflow.add_edge("agent_host", "guard")

    # guard -> conditional routing
    workflow.add_conditional_edges(
        "guard",
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

    # generator -> guard
    workflow.add_edge("generator", "guard")

    # guard -> conditional routing
    workflow.add_conditional_edges(
        "guard",
        route_after_guard,
        {
            "malicious": "fallback_inicial",  # go to fallback_final if malicious
            "continue": END,  # if there's no error ends
        },
    )

    # Compile the graph
    return workflow.compile()
