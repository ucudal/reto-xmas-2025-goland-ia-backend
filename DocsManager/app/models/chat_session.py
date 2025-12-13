from sqlalchemy import (
    Column,
    TIMESTAMP,
    JSON,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from db_connection import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    meta = Column("metadata", JSON)

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan"
    )
