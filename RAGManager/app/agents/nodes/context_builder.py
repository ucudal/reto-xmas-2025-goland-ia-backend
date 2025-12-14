"""Nodo 6: Context Builder - Enriches query with retrieved context."""

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import AgentState

_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    """Lazy initialization of LLM instance."""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-5-nano")
    return _llm


def context_builder(state: AgentState) -> dict:
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
        dict: A dictionary with a "messages" key containing the LLM response
    """
    # TODO: Implement context building and primary LLM call
    # This should:
    # 1. Combine paraphrased_text with relevant_chunks into enriched_query
    # 2. Format the query appropriately (e.g., with system prompts, context sections)
    # 3. Call Primary LLM with the enriched query
    # 4. Store the LLM response in primary_response

    # Placeholder: For now, we'll create a simple enriched query
    chunks = state.get("relevant_chunks", [])

    # Build enriched query with context
    context_section = "\n\n".join(chunks) if chunks else "No relevant context found."

    system_content = f"""You are a helpful assistant. Use the following context to answer the user's question.
If the answer is not in the context, say you don't know.

Context:
{context_section}"""

    messages = [SystemMessage(content=system_content)] + state["messages"]

    # Call Primary LLM
    response = _get_llm().invoke(messages)

    return {"messages": [response]}
