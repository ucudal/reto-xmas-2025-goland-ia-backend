"""Service functions for chat-related operations."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession

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
