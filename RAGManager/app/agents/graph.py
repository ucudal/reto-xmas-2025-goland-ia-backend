"""Main graph definition and construction for the LangGraph agent."""

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    agent_host,
    context_builder,
    fallback,
    guard,
    parafraseo,
    retriever,
)
from app.agents.state import AgentState
from app.agents.routing import route_after_guard

def create_agent_graph() -> StateGraph:
    """
    Create and configure the LangGraph agent graph.

    The graph implements the following flow:
    1. START -> agent_host (Nodo 1) - Prepares state, no DB operations
    2. agent_host -> guard (Nodo 2) - Validates for malicious content
    3. guard -> [conditional]:
       - malicious -> fallback -> END (stops processing, no DB save)
       - continue -> parafraseo (Nodo 4)
    4. parafraseo -> Saves message to DB, retrieves chat history, paraphrases
    5. parafraseo -> retriever (Nodo 5)
    6. retriever -> context_builder (Nodo 6)
    7. context_builder -> guard (validates response)
    8. guard -> [conditional]:
       - malicious -> fallback -> END
       - continue -> END (success)

    Returns:
        Configured StateGraph instance ready for execution
    """
    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent_host", agent_host)
    workflow.add_node("guard", guard)
    workflow.add_node("fallback", fallback)
    workflow.add_node("parafraseo", parafraseo)
    workflow.add_node("retriever", retriever)
    workflow.add_node("context_builder", context_builder)

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
            "malicious": "fallback",  # go to fallback if malicious
            "continue": "parafraseo",  # Continue to parafraseo if valid
        },
    )

    # parafraseo -> retriever
    workflow.add_edge("parafraseo", "retriever")

    # retriever -> context_builder
    workflow.add_edge("retriever", "context_builder")

    # context_builder -> guard
    workflow.add_edge("context_builder", "guard")

    # guard -> conditional routing
    workflow.add_conditional_edges(
        "guard",
        route_after_guard,
        {
            "malicious": "fallback",  # go to fallback if malicious
            "continue": END,  # if there's no error ends
        },
    )
    workflow.add_edge("fallback", END)
    # Compile the graph
    return workflow.compile()
