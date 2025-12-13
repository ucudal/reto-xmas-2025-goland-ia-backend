from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MinIO Configuration
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool = True
    max_pdf_size_mb: int = Field(
        default=100,
        ge=1,
        description="Maximum PDF file size in megabytes that can be loaded into memory.",
    )

    # OpenAI Configuration
    openai_api_key: str

    # Database Configuration
    database_url: str

    # Chunking Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Embedding Configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Guardrails Configuration
    guardrails_jailbreak_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="DetectJailbreak threshold; verify semantics in guardrails-ai (higher vs lower sensitivity).",
    )
    guardrails_device: Literal["cpu", "cuda", "mps"] = Field(
        default="cpu",
        description="Device for model inference.",
    )
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

