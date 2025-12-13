from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MinIO Configuration
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool = True

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
    guardrails_jailbreak_threshold: float = 0.9  # Detection threshold (lower is more sensitive)
    guardrails_device: str = "cpu"  # Device for model inference (cpu, cuda, mps)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

