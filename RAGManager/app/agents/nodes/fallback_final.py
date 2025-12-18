"""Nodo 8: Fallback Final - Stops processing when risky content is detected."""

import logging

from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def fallback_final(state: AgentState) -> AgentState:
    """
    Fallback Final node - Stops processing when risky content is detected.

    This node:
    1. Sets error message indicating that the information requested is classified or not free to know
    2. Stops the flow by routing to END

    Args:
        state: Agent state containing the response flagged as risky

    Returns:
        Updated state with error_message set, ready to route to END
    """
    updated_state = state.copy()

    # Set error message for risky content
    updated_state["error_message"] = "La información solicitada es confidencial o no es de libre acceso."
    logger.warning("Risky content detected. Stopping processing. Response content not logged for security.")

    return updated_state
