"""Nodo 6: Context Builder - Enriches query with retrieved context."""

import logging

from app.agents.state import AgentState
from app.core.config import settings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# Initialize Primary LLM with configuration from settings
llm = ChatOpenAI(
    model="gpt-4.1-mini",  # Primary LLM model for context-aware responses
    openai_api_key=settings.openai_api_key,
)


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
    enriched_query = f"""Pregunta del usuario: {paraphrased}

Contexto relevante de la base de conocimiento:
{context_section}

Por favor, proporciona una respuesta completa basada en el contexto proporcionado arriba. Si el contexto no contiene suficiente información para responder la pregunta, indícalo claramente."""
    
    # System prompt for the Primary LLM
    system_content = """Eres un asistente útil especializado en brindar respuestas precisas y basadas en contexto sobre temas de nutrición y culinaria.

Tu tarea es:
1. Usar el contexto proporcionado para responder la pregunta del usuario con precisión
2. Si el contexto contiene información relevante, proporcionar una respuesta completa
3. Si el contexto no contiene suficiente información, indicar claramente que no cuentas con información suficiente en la base de conocimiento
4. Basar siempre tu respuesta en el contexto proporcionado; no inventes información
5. Si la pregunta no está relacionada con el contexto, redirigir cortésmente la conversación

Sé conciso, preciso y útil."""
    
    # Prepare messages for LLM
    messages_for_llm = [
        SystemMessage(content=system_content),
        HumanMessage(content=enriched_query)
    ]
    
    try:
        # Call Primary LLM
        logger.info("Calling Primary LLM with enriched query")
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
