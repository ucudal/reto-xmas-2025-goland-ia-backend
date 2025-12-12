"""Nodo 2: Guard - Validates for malicious content."""

from app.agents.state import AgentState


def guard(state: AgentState) -> AgentState:
    """
    Guard node - Validates user input for malicious content.

    This node:
    1. Analyzes the prompt for malicious patterns
    2. Sets is_malicious flag
    3. Sets error_message if malicious content is detected

    Args:
        state: Agent state containing the prompt

    Returns:
        Updated state with is_malicious and error_message set
    """
    # TODO: Implement malicious content detection
    # This should:
    # 1. Check for injection attacks, prompt injection, etc.
    # 2. Use appropriate validation libraries or models
    # 3. Set is_malicious = True if malicious content is detected
    # 4. Set error_message with appropriate message

    # Placeholder: For now, we'll assume all prompts are safe
    updated_state = state.copy()
    updated_state["is_malicious"] = False
    updated_state["error_message"] = None

    return updated_state
