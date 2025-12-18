"""Nodo 1: Agent Host - Entry point that prepares initial state."""

import logging
from uuid import UUID

from app.agents.state import AgentState
from app.core.database_connection import SessionLocal
from app.repositories.chat_repository import get_chat_history

logger = logging.getLogger(__name__)


def agent_host(state: AgentState) -> AgentState:
    """
    Agent Host node - Entry point for the agent flow.

    This node:
    1. Receives the initial prompt and optional chat_session_id
    2. Extracts the prompt from messages
    3. Retrieves chat history if session_id is provided
    4. Prepares state with context for the entire flow
    
    Note: Chat history is retrieved here (not in parafraseo) so it's available
    throughout the entire flow, regardless of which path is taken (normal or fallback).

    Args:
        state: Agent state containing the user prompt and optional chat_session_id

    Returns:
        Updated state with prompt, chat_messages, and initial_context set
    """
    updated_state = state.copy()
    
    # Extract prompt from messages
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    prompt = last_message.content if last_message else ""

    # Set prompt and initial context
    updated_state["prompt"] = prompt
    updated_state["initial_context"] = prompt

    # Retrieve chat history if session exists
    chat_session_id = state.get("chat_session_id")
    
    if chat_session_id:
        try:
            # Convert to UUID if string
            session_uuid = UUID(chat_session_id) if isinstance(chat_session_id, str) else chat_session_id
            
            db = SessionLocal()
            try:
                # Get chat history from database
                chat_messages = get_chat_history(db, session_uuid)
                
                # Convert SQLAlchemy models to dicts for state
                updated_state["chat_messages"] = [
                    {
                        "id": msg.id,
                        "sender": msg.sender,
                        "message": msg.message,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    }
                    for msg in chat_messages
                ]
                
                logger.info(f"Retrieved {len(chat_messages)} messages for session {session_uuid}")
            finally:
                db.close()
                
        except ValueError as e:
            # Session doesn't exist - this is okay for new sessions
            logger.info(f"Chat session not found (likely new session): {e}")
            updated_state["chat_messages"] = []
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}", exc_info=True)
            updated_state["chat_messages"] = []
    else:
        # No session ID provided - new conversation
        logger.info("No chat_session_id provided - starting new conversation")
        updated_state["chat_messages"] = []

    logger.debug(f"Agent host prepared state with {len(updated_state.get('chat_messages', []))} chat messages")

    return updated_state
