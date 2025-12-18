"""Pydantic schemas for chat-related endpoints."""

from datetime import datetime
from uuid import UUID

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
