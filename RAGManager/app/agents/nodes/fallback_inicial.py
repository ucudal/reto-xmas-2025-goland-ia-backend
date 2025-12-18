"""Nodo 3: Fallback Inicial - Stops processing when malicious content is detected."""

import logging

from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def fallback_inicial(state: AgentState) -> AgentState:
    """
    Fallback Inicial node - Stops processing when malicious content is detected.

    This node:
    1. Sets error message indicating that the user's intentions break the chatbot's rules
    2. Stops the flow by routing to END

    Args:
        state: Agent state containing the prompt flagged as malicious

    Returns:
        Updated state with error_message set, ready to route to END
    """
    updated_state = state.copy()

    # Set error message for malicious content
    updated_state["error_message"] = "La intención del usuario infringe las reglas del chatbot."
    logger.warning("Malicious content detected. Stopping processing. Prompt content not logged for security.")

    return updated_state
