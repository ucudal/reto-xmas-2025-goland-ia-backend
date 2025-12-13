"""Models for chat sessions and messages."""

from datetime import datetime

from sqlalchemy import Column, Enum, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database_connection import Base


class ChatSession(Base):
    """Model for chat_sessions table - stores chat conversation sessions."""

    __tablename__ = "chat_sessions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default="uuid_generate_v4()")
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    metadata = Column(JSONB, nullable=True)

    # Relationship to messages
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Model for chat_messages table - stores individual messages in a chat session."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender = Column(
        Enum("user", "assistant", "system", name="sender_type", create_type=False),
        nullable=False,
    )
    message = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Relationship to session
    session = relationship("ChatSession", back_populates="messages")
