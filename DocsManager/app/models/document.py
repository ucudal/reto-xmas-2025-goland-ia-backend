from datetime import datetime

from sqlalchemy import Column, Integer, Text, TIMESTAMP
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
