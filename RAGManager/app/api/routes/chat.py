"""API routes for chat-related endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database_connection import get_db
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageResponse,
    UserMessageRequest,
    AssistantMessageResponse,
)
from app.repositories.chat_repository import get_chat_history
from app.services.chat import create_user_message_and_process

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


@router.post("/messages", response_model=AssistantMessageResponse)
def post_user_message(
    request: UserMessageRequest,
    db: Session = Depends(get_db),
) -> AssistantMessageResponse:
    """
    Process a user message through the complete chat flow.

    This endpoint:
    1. Creates or retrieves a chat session
    2. Saves the user's message to the database
    3. Processes the message through the LangGraph agent (guards, paraphrase, retrieval, generation)
    4. Saves the assistant's response to the database
    5. Returns the assistant's response to the user

    Args:
        request: UserMessageRequest containing the message and optional session_id
        db: Database session dependency

    Returns:
        AssistantMessageResponse containing session_id and the assistant's message

    Raises:
        HTTPException: 400 for validation errors (empty message, invalid session)
        HTTPException: 500 for processing errors
    """
    logger.info(f"Received user message for session: {request.session_id}")

    try:
        # Process complete flow: save user msg, run agent, save assistant msg
        assistant_msg, session_id = create_user_message_and_process(
            db=db,
            message=request.message,
            session_id=request.session_id,
        )

        return AssistantMessageResponse(
            session_id=session_id,
            message=assistant_msg.message,
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
