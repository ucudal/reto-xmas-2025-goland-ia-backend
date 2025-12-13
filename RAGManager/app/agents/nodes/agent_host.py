"""Nodo 1: Agent Host - Entry point that saves initial context."""

import logging
from uuid import UUID, uuid4

from app.agents.state import AgentState
from app.core.database_connection import SessionLocal
from app.models.chat import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


def agent_host(state: AgentState) -> AgentState:
    """
    Agent Host node - Entry point for the agent flow.

    This node:
    1. Receives the initial prompt and optional chat_session_id
    2. Creates or retrieves chat session from PostgreSQL
    3. Saves the user's message to the chat session
    4. Retrieves all chat messages for the session
    5. Prepares state for validation

    Args:
        state: Agent state containing the user prompt and optional chat_session_id

    Returns:
        Updated state with chat_session_id, chat_messages, and initial_context set
    """
    updated_state = state.copy()
    prompt = state.get("prompt", "")
    chat_session_id = state.get("chat_session_id")

    db = None
    try:
        db = SessionLocal()
        # Get or create chat session
        chat_session = None
        if chat_session_id:
            try:
                session_uuid = UUID(chat_session_id)
                chat_session = db.query(ChatSession).filter(ChatSession.id == session_uuid).first()
                if not chat_session:
                    logger.warning(f"Chat session {chat_session_id} not found, creating new session")
            except (ValueError, TypeError):
                logger.warning(f"Invalid chat_session_id format: {chat_session_id}, creating new session")
        
        # Create new session if needed
        if not chat_session:
            chat_session = ChatSession(id=uuid4())
            db.add(chat_session)
            db.flush()

        # Create new message with user's prompt
        new_message = ChatMessage(
            session_id=chat_session.id,
            sender="user",
            message=prompt,
        )
        db.add(new_message)
        db.flush()

        # Query all messages for the session ordered by created_at
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == chat_session.id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

        # Convert messages to dictionaries
        chat_messages = [
            {
                "id": msg.id,
                "session_id": str(msg.session_id),
                "sender": msg.sender,
                "message": msg.message,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ]

        # Commit the transaction
        db.commit()

        # Update state
        updated_state["chat_session_id"] = str(chat_session.id)
        updated_state["chat_messages"] = chat_messages
        updated_state["initial_context"] = prompt

        logger.info(f"Chat session {chat_session.id} updated with {len(chat_messages)} messages")

    except Exception as e:
        # Rollback on error
        if db is not None:
            db.rollback()
        logger.error(f"Error in agent_host: {e}", exc_info=True)
        # Set error state but don't fail completely
        updated_state["chat_session_id"] = None
        updated_state["chat_messages"] = None
        updated_state["initial_context"] = prompt
    finally:
        if db is not None:
            db.close()

    return updated_state
