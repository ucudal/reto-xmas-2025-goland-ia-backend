from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Integer, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.db_connection import Base


class DocumentChunk(Base):
    """Model for document_chunks table - stores document chunks with embeddings."""

    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Relationship to document
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="unique_document_chunk"),
    )