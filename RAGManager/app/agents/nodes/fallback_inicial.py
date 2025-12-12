"""Nodo 3: Fallback Inicial - Initial fallback processing."""

from app.agents.state import AgentState


def fallback_inicial(state: AgentState) -> AgentState:
    """
    Fallback Inicial node - Performs initial fallback processing.

    This node:
    1. Adjusts the text if needed (e.g., formatting, normalization)
    2. Prepares text for paraphrasing step

    Args:
        state: Agent state containing the prompt or initial context

    Returns:
        Updated state with adjusted_text set (if applicable)
    """
    # TODO: Implement initial fallback logic
    # This should:
    # 1. Normalize text (remove extra spaces, fix encoding, etc.)
    # 2. Apply any necessary text adjustments
    # 3. Set adjusted_text if adjustments were made, otherwise None

    # Placeholder: For now, we'll use the prompt as-is
    updated_state = state.copy()
    prompt = state.get("prompt", "")
    updated_state["adjusted_text"] = prompt if prompt else None

    return updated_state
