"""Nodo 7: Generator - Processes LLM response."""

from app.agents.state import AgentState


def generator(state: AgentState) -> AgentState:
    """
    Generator node - Processes the response from Primary LLM.

    This node:
    1. Takes the primary_response from Primary LLM
    2. Processes/transforms the response as needed
    3. Prepares response for final validation

    Args:
        state: Agent state containing primary_response

    Returns:
        Updated state with generated_response set
    """
    # TODO: Implement response processing/generation logic
    # This should:
    # 1. Process the primary_response (formatting, extraction, etc.)
    # 2. Apply any necessary transformations
    # 3. Set generated_response with the processed result

    # Placeholder: For now, we'll use the primary_response as-is
    updated_state = state.copy()
    updated_state["generated_response"] = state.get("primary_response")

    return updated_state
