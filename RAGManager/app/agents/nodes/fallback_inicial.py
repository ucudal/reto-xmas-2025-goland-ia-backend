"""Nodo 3: Fallback Inicial - Initial fallback processing."""

import logging

from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def fallback_inicial(state: AgentState) -> AgentState:
    """
    Fallback Inicial node - Performs initial fallback processing.

    This node:
    1. Defensively checks if the prompt was flagged as malicious
    2. Adjusts the text if needed (e.g., formatting, normalization)
    3. Prepares text for paraphrasing step

    Args:
        state: Agent state containing the prompt or initial context

    Returns:
        Updated state with adjusted_text set (if applicable) or error_message if malicious
    """
    updated_state = state.copy()

    # Defensive check: Verify that the prompt was not flagged as malicious
    # This should not happen due to routing, but serves as an extra safety layer
    if state.get("is_malicious", False):
        logger.warning(
            "Defensive check triggered: Malicious prompt reached fallback_inicial node. "
            "This indicates a potential routing issue."
        )
        updated_state["error_message"] = "The requested information or action is not possible by the agent."
        updated_state["adjusted_text"] = None
        return updated_state

    # TODO: Implement initial fallback logic
    # This should:
    # 1. Normalize text (remove extra spaces, fix encoding, etc.)
    # 2. Apply any necessary text adjustments
    # 3. Set adjusted_text if adjustments were made, otherwise None

    # Placeholder: For now, we'll use the prompt as-is
    prompt = state.get("prompt", "")
    updated_state["adjusted_text"] = prompt if prompt else None

    return updated_state
