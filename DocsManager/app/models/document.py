from datetime import datetime

from sqlalchemy import Column, Integer, Text, TIMESTAMP

from app.core.db_connection import Base


class Document(Base):
    """Model for documents table - stores PDF metadata uploaded to MinIO."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(Text, nullable=False)
    minio_path = Column(Text, nullable=False)
    uploaded_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
