"""Nodo 6: Context Builder - Enriches query with retrieved context."""

from app.agents.state import AgentState


def context_builder(state: AgentState) -> AgentState:
    """
    Context Builder node - Enriches query with retrieved context.

    This node:
    1. Takes paraphrased text and relevant chunks
    2. Builds an enriched query combining both
    3. Calls Primary LLM with the enriched query
    4. Gets response from Primary LLM

    Args:
        state: Agent state containing paraphrased_text and relevant_chunks

    Returns:
        Updated state with enriched_query and primary_response set
    """
    # TODO: Implement context building and primary LLM call
    # This should:
    # 1. Combine paraphrased_text with relevant_chunks into enriched_query
    # 2. Format the query appropriately (e.g., with system prompts, context sections)
    # 3. Call Primary LLM with the enriched query
    # 4. Store the LLM response in primary_response

    # Placeholder: For now, we'll create a simple enriched query
    updated_state = state.copy()
    paraphrased = state.get("paraphrased_text", "")
    chunks = state.get("relevant_chunks", [])

    # Build enriched query
    context_section = "\n\n".join(chunks) if chunks else ""
    enriched_query = f"{paraphrased}\n\nContext:\n{context_section}" if context_section else paraphrased
    updated_state["enriched_query"] = enriched_query

    # TODO: Call Primary LLM here
    # updated_state["primary_response"] = call_primary_llm(enriched_query)
    updated_state["primary_response"] = None

    return updated_state
