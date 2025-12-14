from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Integer, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.db_connection import Base


class Document(Base):
    """Model for documents table - stores PDF metadata."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(Text, nullable=False)
    minio_path = Column(Text, nullable=False)
    uploaded_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Relationship to chunks
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Model for document_chunks table - stores document chunks with embeddings."""

    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
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

