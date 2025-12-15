from pydantic import BaseModel
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """Response from the upload endpoint"""

    id: int
    filename: str
    status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """Response for getting a document"""

    id: int
    filename: str
    minio_path: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response for listing documents"""

    id: int
    filename: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class DocumentListPaginatedResponse(BaseModel):
    """Paginated response for listing documents"""

    documents: list[DocumentListResponse]
    total: int
    limit: int
    offset: int

    class Config:
        from_attributes = True

