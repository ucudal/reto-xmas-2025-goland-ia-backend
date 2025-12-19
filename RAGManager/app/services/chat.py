"""Service functions for chat-related operations."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession

logger = logging.getLogger(__name__)


def get_chat_history(db: Session, session_id: UUID) -> list[ChatMessage]:
    """
    Retrieve the last 10 messages from a chat session.

    Args:
        db: SQLAlchemy database session
        session_id: UUID of the chat session

    Returns:
        List of ChatMessage objects ordered by created_at DESC (most recent first)

    Raises:
        ValueError: If the chat session doesn't exist
    """
    # First, validate that the session exists
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise ValueError(f"Chat session {session_id} not found")

    # Query the last 10 messages for this session, ordered by created_at DESC
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
        .all()
    )

    # Reverse to get chronological order (oldest first)
    # But the plan says "most recent first", so we'll keep DESC order
    logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
    return messages


def save_user_message(db: Session, message: str, session_id: UUID | None = None) -> tuple[ChatMessage, UUID]:
    """
    Save a user message to a chat session.

    Args:
        db: SQLAlchemy database session
        message: The user's message text
        session_id: UUID of the chat session (optional - creates new session if not provided)

    Returns:
        Tuple of (saved ChatMessage object, session_id UUID)

    Raises:
        ValueError: If the provided session_id doesn't exist
    """
    # 1. If no session_id provided, create a new session
    if not session_id:
        session = ChatSession()
        db.add(session)
        db.flush()  # Generate UUID without committing
        session_id = session.id
        logger.info(f"Created new chat session: {session_id}")
    else:
        # Validate that the session exists
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise ValueError(f"Chat session {session_id} not found")

    # 2. Create and save the user message
    user_message = ChatMessage(
        session_id=session_id,
        sender="user",
        message=message
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    logger.info(f"Saved user message to session {session_id}")
    return user_message, session_id
