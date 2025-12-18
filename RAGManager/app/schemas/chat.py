"""Pydantic schemas for chat-related endpoints."""

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class ChatMessageResponse(BaseModel):
    """Response schema for a single chat message."""

    id: int
    session_id: UUID
    sender: str  # 'user', 'assistant', or 'system'
    message: str
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history endpoint."""

    session_id: UUID
    messages: list[ChatMessageResponse]
    count: int


class UserMessageRequest(BaseModel):
    """Request schema for posting a user message."""

    message: str
    session_id: Optional[UUID] = None


class AssistantMessageResponse(BaseModel):
    """Response schema for assistant message."""

    session_id: UUID
    message: str
