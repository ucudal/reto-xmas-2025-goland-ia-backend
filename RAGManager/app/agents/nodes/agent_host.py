"""Nodo 1: Agent Host - Entry point that saves initial context."""

from app.agents.state import AgentState


def agent_host(state: AgentState) -> AgentState:
    """
    Agent Host node - Entry point for the agent flow.

    This node:
    1. Receives the initial prompt
    2. Saves initial context to PostgreSQL
    3. Prepares state for validation

    Args:
        state: Agent state containing the user prompt

    Returns:
        Updated state with initial_context set
    """
    # TODO: Implement database connection and save initial context
    # This should:
    # 1. Connect to PostgreSQL database
    # 2. Save the prompt and any metadata as initial context
    # 3. Store the context_id or reference in initial_context

    # Placeholder: For now, we'll just store the prompt as initial context
    updated_state = state.copy()
    initial_message = state["messages"][-1]
    updated_state["initial_context"] = (
        initial_message.content if initial_message else ""
    )

    return updated_state
