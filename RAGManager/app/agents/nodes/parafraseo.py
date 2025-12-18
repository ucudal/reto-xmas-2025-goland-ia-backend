"""Nodo 4: Parafraseo - Saves message and paraphrases user input using chat history."""

import json
import logging
from uuid import UUID

from app.agents.state import AgentState
from app.core.database_connection import SessionLocal
from app.repositories.chat_repository import save_user_message
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-5-nano")


def parafraseo(state: AgentState) -> AgentState:
    """
    Parafraseo node - Saves message to DB and paraphrases user input using chat history.

    This node:
    1. Receives a validated user message (after guard_inicial validation)
    2. Saves the user's message to the chat session in PostgreSQL using save_user_message service
    3. Uses chat history (already retrieved by agent_host) as context
    4. Uses the last message to understand user's intentions and chat history as context
    5. Sends to LLM with instructions to return 3 differently phrased statements that encapsulate
       the user's intentions according to the last message and chat history

    Args:
        state: Agent state containing validated user message, chat_messages (from agent_host), 
               chat_session_id (optional - creates new session if not provided)

    Returns:
        Updated state with chat_session_id (if new), paraphrased_text and paraphrased_statements
    """
    updated_state = state.copy()
    
    # Get the validated user message from state
    messages = state.get("messages", [])
    if not messages:
        logger.error("No messages found in state")
        updated_state["error_message"] = "No user message found in state"
        return updated_state
    
    # Get the last message (the validated user message)
    last_user_message = messages[-1]
    user_message_content = last_user_message.content if hasattr(last_user_message, 'content') else str(last_user_message)
    
    # Save validated message to PostgreSQL database
    chat_session_id = state.get("chat_session_id")
    
    try:
        # Convert session_id to UUID if provided
        session_uuid = UUID(chat_session_id) if chat_session_id and isinstance(chat_session_id, str) else chat_session_id
        
        db = SessionLocal()
        try:
            # Save the user message to the database
            saved_message, resulting_session_id = save_user_message(
                db=db,
                message=user_message_content,
                session_id=session_uuid
            )
            
            # Update state with session_id (important for new sessions)
            updated_state["chat_session_id"] = str(resulting_session_id)
            
            logger.info(f"Saved user message (ID: {saved_message.id}) to session {resulting_session_id}")
            
        finally:
            db.close()
            
    except ValueError as e:
        # Session not found or invalid
        logger.error(f"Error saving message: {e}")
        updated_state["error_message"] = f"Failed to save message: {str(e)}"
        return updated_state
    except Exception as e:
        # Other database errors
        logger.error(f"Unexpected error saving message: {e}", exc_info=True)
        updated_state["error_message"] = f"Failed to save message: {str(e)}"
        return updated_state
    
    # Get chat history from state (already retrieved by agent_host)
    chat_messages = state.get("chat_messages", [])
    logger.info(f"Using {len(chat_messages)} chat messages from state (retrieved by agent_host)")
    
    # Process chat history: last message (intentions) + 9 older messages (context)
    # The last message is the most recent one (for understanding intentions)
    # The remaining 9 messages are older (for context)
    if len(chat_messages) >= 10:
        # We have 10+ messages: use last one for intentions, previous 9 for context
        context_messages = chat_messages[-10:-1]  # 9 older messages
        intention_message = chat_messages[-1]  # Last message (most recent)
    elif len(chat_messages) > 1:
        # We have 2-9 messages: use last one for intentions, all previous for context
        context_messages = chat_messages[:-1]  # All older messages
        intention_message = chat_messages[-1]  # Last message
    else:
        # We have only 1 message: use it for intentions, no context
        context_messages = []
        intention_message = chat_messages[0] if chat_messages else {"sender": "user", "message": user_message_content}
    
    # Format chat history for LLM prompt
    # Each message should clearly indicate if it was sent by the user or the agent
    def format_message_with_sender(msg: dict) -> str:
        """Format a message with explicit sender label."""
        sender = msg.get("sender", "unknown").lower()
        message = msg.get("message", "")
        
        # Normalize sender labels for clarity
        if sender == "user":
            sender_label = "User"
        elif sender == "assistant":
            sender_label = "Assistant"
        elif sender == "system":
            sender_label = "System"
        else:
            sender_label = sender.capitalize()
        
        return f"{sender_label}: {message}"
    
    context_text = ""
    if context_messages:
        context_lines = []
        for msg in context_messages:
            context_lines.append(format_message_with_sender(msg))
        context_text = "\n".join(context_lines)
    
    # Format the intention message with sender information
    intention_sender = intention_message.get("sender", "user").lower()
    intention_message_text = intention_message.get("message", user_message_content)
    
    # Format intention message with sender label
    if intention_sender == "user":
        intention_label = "User"
    elif intention_sender == "assistant":
        intention_label = "Assistant"
    elif intention_sender == "system":
        intention_label = "System"
    else:
        intention_label = intention_sender.capitalize()
    
    intention_text = f"{intention_label}: {intention_message_text}"
    
    # Create LLM prompt with instructions
    system_instruction = """Eres un experto en comprender las intenciones del usuario y parafrasearlas de diferentes maneras.

Dado el último mensaje del usuario y el historial de la conversación, tu tarea es devolver exactamente 3 enunciados formulados de manera distinta que encapsulen la intención del usuario.

El último mensaje representa lo que el usuario quiere saber o hacer ahora mismo. El historial de la conversación aporta contexto sobre lo que se ha estado tratando.

Requisitos:
- Devuelve exactamente 3 formulaciones diferentes
- Cada formulación debe capturar la intención principal del usuario a partir de su último mensaje
- Usa el historial para entender el contexto y las referencias (por ejemplo, "eso", "lo anterior", "aquello")
- Cada formulación debe ser un enunciado completo e independiente, que se entienda sin necesidad de toda la conversación
- Las formulaciones deben ser diversas: usa palabras, estructuras y perspectivas distintas
- Formatea tu respuesta como un array JSON de exactamente 3 strings: ["enunciado 1", "enunciado 2", "enunciado 3"]
- No incluyas ninguna explicación: solo el array JSON

Formato de ejemplo:
["¿Cuáles son las características principales del producto?", "¿Puedes explicar los aspectos clave de este producto?", "Me gustaría saber qué ofrece este producto."]"""

    # Build the prompt with context and intention
    # Both context and intention messages now clearly show sender (User/Assistant/System)
    if context_text:
        user_prompt = f"""Historial de la conversación (mensajes anteriores para contexto):
{context_text}

Último mensaje (intención actual):
{intention_text}

Devuelve 3 enunciados formulados de manera distinta que encapsulen la intención del usuario a partir de su último mensaje, usando el historial como contexto."""
    else:
        user_prompt = f"""Mensaje (intención actual):
{intention_text}

Devuelve 3 enunciados formulados de manera distinta que encapsulen la intención del usuario a partir de su mensaje."""

    # Call LLM with the prompt
    messages_for_llm = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm.invoke(messages_for_llm)
        response_content = response.content.strip()
        
        # Parse the JSON response to extract the 3 statements
        try:
            # Try to parse as JSON array
            paraphrased_statements = json.loads(response_content)
            if isinstance(paraphrased_statements, list) and len(paraphrased_statements) >= 3:
                # Take the first 3 statements
                paraphrased_statements = paraphrased_statements[:3]
            elif isinstance(paraphrased_statements, list):
                # If less than 3, pad with the last one or use as-is
                while len(paraphrased_statements) < 3:
                    paraphrased_statements.append(paraphrased_statements[-1] if paraphrased_statements else intention_text)
            else:
                # If not a list, create a list with the response
                paraphrased_statements = [response_content, response_content, response_content]
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract statements from text
            logger.warning("LLM response is not valid JSON, attempting to parse as text")
            # Try to split by newlines or common separators
            lines = [line.strip() for line in response_content.split('\n') if line.strip()]
            if len(lines) >= 3:
                paraphrased_statements = lines[:3]
            else:
                # Fallback: use the response as-is and duplicate if needed
                paraphrased_statements = [response_content] * 3
        
        # Store the results
        updated_state["paraphrased_statements"] = paraphrased_statements
        # Store the first statement in paraphrased_text for backward compatibility
        updated_state["paraphrased_text"] = paraphrased_statements[0] if paraphrased_statements else intention_text
        
        logger.info(f"Generated {len(paraphrased_statements)} paraphrased statements")
        
    except Exception as e:
        logger.error(f"Error calling LLM for paraphrasing: {e}")
        # Fallback: use the original message
        updated_state["paraphrased_statements"] = [intention_text, intention_text, intention_text]
        updated_state["paraphrased_text"] = intention_text
        updated_state["error_message"] = f"Error in paraphrasing: {str(e)}"

    return updated_state
