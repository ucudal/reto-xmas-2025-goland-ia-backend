"""Nodo 6: Context Builder - Enriches query with retrieved context."""

import logging

from app.agents.state import AgentState
from app.core.config import settings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# Lazy initialization to avoid loading API key at import time
_llm = None

def _get_llm():
    """Get or create the LLM instance."""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="gpt-4o-mini",  # Primary LLM model for context-aware responses
            openai_api_key=settings.openai_api_key,
        )
    return _llm


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
    updated_state = state.copy()
    
    # Get paraphrased text and relevant chunks from state
    paraphrased = state.get("paraphrased_text", "")
    chunks = state.get("relevant_chunks", [])
    
    # Fallback if paraphrased_text is not available
    if not paraphrased:
        logger.warning("No paraphrased text found in state. Using original prompt.")
        messages = state.get("messages", [])
        if messages:
            paraphrased = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
        else:
            paraphrased = state.get("prompt", "")
    
    # Build enriched query with context
    if chunks:
        context_section = "\n\n---\n\n".join([f"Context {i+1}:\n{chunk}" for i, chunk in enumerate(chunks)])
    else:
        context_section = "No relevant context found in the knowledge base."
        logger.warning("No relevant chunks found for context building")
    
    # Create enriched query combining paraphrased text and context
    enriched_query = f"""User Question: {paraphrased}

Relevant Context from Knowledge Base:
{context_section}

Please provide a comprehensive answer based on the context provided above. If the context does not contain enough information to answer the question, please indicate that clearly."""
    
    # System prompt for the Primary LLM
    system_content = """You are a helpful assistant specialized in providing accurate, context-based answers about nutrition and culinary topics.

Your task is to:
1. Use the provided context to answer the user's question accurately
2. If the context contains relevant information, provide a comprehensive answer
3. If the context does not contain enough information, clearly state that you don't have sufficient information in the knowledge base
4. Always base your answer on the provided context - do not make up information
5. If the question is not related to the context, politely redirect the conversation

Be concise, accurate, and helpful."""
    
    # Prepare messages for LLM
    messages_for_llm = [
        SystemMessage(content=system_content),
        HumanMessage(content=enriched_query)
    ]
    
    try:
        # Call Primary LLM
        logger.info("Calling Primary LLM with enriched query")
        llm = _get_llm()
        response = llm.invoke(messages_for_llm)
        
        # Extract response content
        primary_response = response.content if hasattr(response, "content") else str(response)
        
        # Update state with enriched query and primary response (as defined in state.py)
        updated_state["enriched_query"] = enriched_query
        updated_state["primary_response"] = primary_response
        
        # Also set generated_response for guard_final (Nodo 7: Generator not yet implemented)
        # For now, generated_response = primary_response
        # This allows guard_final to validate the response
        updated_state["generated_response"] = primary_response
        
        # Also update messages for LangGraph compatibility
        updated_state["messages"] = state.get("messages", []) + [response]
        
        logger.info("Successfully generated primary response from LLM")
        
    except Exception as e:
        logger.error(f"Error calling Primary LLM: {e}", exc_info=True)
        # Set error state
        updated_state["error_message"] = f"Error in context builder: {str(e)}"
        updated_state["enriched_query"] = enriched_query
        updated_state["primary_response"] = None
        updated_state["generated_response"] = None
        
    return updated_state
