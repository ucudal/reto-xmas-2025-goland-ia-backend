"""State schema definition for the LangGraph agent."""

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """
    State schema for the agent graph.

    This TypedDict defines all the state variables that flow through
    the LangGraph nodes during agent execution.
    """

    # Input
    # prompt attribute removed as it is replaced by messages in MessagesState

    # Nodo 1: Agent Host
    initial_context: str | None  # Context saved to PostgreSQL
    chat_messages: list[dict] | None  # List of all chat messages for the session

    # Nodo 2: Guard
    is_malicious: bool  # Flag indicating if prompt is malicious
    error_message: str | None  # Error message if validation fails

    # Nodo 3: Fallback Inicial
    adjusted_text: str | None  # Text adjusted by initial fallback (if applicable)

    # Nodo 4: Parafraseo
    paraphrased_text: str | None  # Paraphrased text from Parafraseo node

    # Nodo 5: Retriever
    relevant_chunks: list[str] | None  # Chunks retrieved from vector DB

    # Nodo 6: Context Builder
    enriched_query: str | None  # Query enriched with context

    # Primary LLM (called within context_builder)
    primary_response: str | None  # Response from primary LLM

    # Nodo 7: Generator
    generated_response: str | None  # Processed response from generator

    # Nodo 8: Fallback Final
    is_risky: bool  # Flag indicating if response is risky/sensitive

    # Final LLM (called within fallback_final)
    final_response: str | None  # Final processed response
