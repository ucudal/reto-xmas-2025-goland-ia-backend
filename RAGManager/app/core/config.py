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
    minio_use_ssl: bool = True

    # OpenAI Configuration
    openai_api_key: str

    # Database Configuration
    database_url: str

    # RabbitMQ Configuration
    rabbitmq_user: str
    rabbitmq_password: str
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_queue_name: str = "document.process"

    # Chunking Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Embedding Configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Chat Configuration
    chat_message_limit: int = Field(
        default=50,
        ge=1,
        description="Maximum number of chat messages to load per session (most recent messages)",
    )

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
    guardrails_pii_entities: list[str] = Field(
        default=[
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "SSN",
            "US_PASSPORT",
            "US_DRIVER_LICENSE",
            "IBAN_CODE",
            "IP_ADDRESS",
        ],
        description="List of PII entity types to detect using DetectPII validator.",
    )
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def rabbitmq_url(self) -> str:
        """Returns the RabbitMQ connection URL with URL-encoded credentials."""
        from urllib.parse import quote_plus

        encoded_user = quote_plus(self.rabbitmq_user)
        encoded_password = quote_plus(self.rabbitmq_password)
        return f"amqp://{encoded_user}:{encoded_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"


settings = Settings()

