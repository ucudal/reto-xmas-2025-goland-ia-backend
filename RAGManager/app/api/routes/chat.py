"""API routes for chat-related endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database_connection import get_db
from app.schemas.chat import ChatHistoryResponse, ChatMessageResponse
from app.services.chat import get_chat_history

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/history/{chat_session_id}", response_model=ChatHistoryResponse)
async def get_chat_history_endpoint(
    chat_session_id: UUID,
    db: Session = Depends(get_db),
) -> ChatHistoryResponse:
    """
    Retrieve the last 10 messages from a chat session.

    This endpoint returns the most recent 10 messages from the specified chat session,
    ordered by creation time (most recent first).

    Args:
        chat_session_id: UUID of the chat session
        db: Database session dependency

    Returns:
        ChatHistoryResponse containing the session_id, list of messages, and count

    Raises:
        HTTPException: 404 if chat session doesn't exist
        HTTPException: 400 if invalid UUID format
        HTTPException: 500 for database errors
    """
    logger.info(f"Received chat history request for session: {chat_session_id}")

    try:
        # Get chat history from service
        messages = get_chat_history(db, chat_session_id)

        # Convert SQLAlchemy models to Pydantic models
        message_responses = [
            ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                sender=msg.sender,
                message=msg.message,
                created_at=msg.created_at,
            )
            for msg in messages
        ]

        return ChatHistoryResponse(
            session_id=chat_session_id,
            messages=message_responses,
            count=len(message_responses),
        )

    except ValueError as e:
        logger.warning(f"Chat session not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
