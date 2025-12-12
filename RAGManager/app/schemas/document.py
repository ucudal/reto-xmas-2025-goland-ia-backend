from pydantic import BaseModel, field_validator


class ProcessPDFRequest(BaseModel):
    """Request schema for PDF processing endpoint."""

    minio_url: str

    @field_validator("minio_url")
    @classmethod
    def validate_minio_url(cls, v: str) -> str:
        """Validate that the URL is a valid HTTP/HTTPS URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("minio_url must be a valid HTTP or HTTPS URL")
        return v


class ProcessPDFResponse(BaseModel):
    """Response schema for PDF processing endpoint."""

    status: str
    document_id: int | None = None
    message: str

