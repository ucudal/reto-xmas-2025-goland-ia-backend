"""Nodo 4: Parafraseo - Paraphrases user input."""

from app.agents.state import AgentState


def parafraseo(state: AgentState) -> AgentState:
    """
    Parafraseo node - Paraphrases the user input.

    This node:
    1. Takes the adjusted text from Fallback Inicial
    2. Paraphrases it to improve clarity or adjust format
    3. Prepares text for retrieval step

    Args:
        state: Agent state containing adjusted_text

    Returns:
        Updated state with paraphrased_text set
    """
    # TODO: Implement paraphrasing logic
    # This should:
    # 1. Use an LLM or paraphrasing model to rephrase the text
    # 2. Improve clarity, adjust tone, or format as needed
    # 3. Set paraphrased_text with the result

    # Placeholder: For now, we'll use the adjusted_text as-is
    updated_state = state.copy()
    text_to_paraphrase = state.get("adjusted_text") or state.get("prompt", "")
    updated_state["paraphrased_text"] = text_to_paraphrase

    return updated_state
