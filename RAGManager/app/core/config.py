from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # PostgreSQL Configuration
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # RabbitMQ Configuration
    rabbitmq_user: str
    rabbitmq_password: str
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_management_port: int = 15672

    # MinIO Configuration
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "documents"
    minio_use_ssl: bool = True

    # OpenAI Configuration
    openai_api_key: str = ""

    # Database Configuration (for SQLAlchemy)
    database_url: str = ""

    # Application
    queue_name: str = "document.process"

    # Chunking Configuration
    chunk_size: int = 500  # Size of each chunk in words
    chunk_overlap: int = 50  # Overlap between chunks in words

    # Embedding Configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def model_post_init(self, __context):
        """Validation after initializing the model"""
        # Build database_url if not provided
        if not self.database_url:
            self.database_url = (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )

        # Validate that rabbitmq_host is not empty
        if not self.rabbitmq_host or self.rabbitmq_host.strip() == "":
            logger.warning("RABBITMQ_HOST is empty, using 'localhost' as default")
            self.rabbitmq_host = "localhost"

        # If host is 'rabbitmq' (Docker service name), change to localhost
        # because the app runs outside Docker
        if self.rabbitmq_host.strip() == "rabbitmq":
            logger.warning(
                "RABBITMQ_HOST='rabbitmq' detected. Changing to 'localhost' because app runs outside Docker"
            )
            self.rabbitmq_host = "localhost"

        # Validate that rabbitmq_user and password are not empty
        if not self.rabbitmq_user or not self.rabbitmq_password:
            logger.error("RABBITMQ_USER and RABBITMQ_PASSWORD are required")

    @property
    def postgres_dsn(self) -> str:
        """Returns the PostgreSQL DSN"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def rabbitmq_url(self) -> str:
        """Returns the RabbitMQ connection URL"""
        # Ensure host is not empty
        host = self.rabbitmq_host.strip() if self.rabbitmq_host else "localhost"
        url = f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{host}:{self.rabbitmq_port}/"
        logger.debug(f"RabbitMQ URL: amqp://{self.rabbitmq_user}:***@{host}:{self.rabbitmq_port}/")
        return url


settings = Settings()

