from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator, Field
from typing import Optional
from urllib.parse import quote_plus
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
    minio_bucket: str = "goland-bucket"
    minio_use_ssl: bool = True
    minio_folder: str = "rag-docs"  # Folder within bucket for RAG documents

    # Database Configuration (for SQLAlchemy)
    database_url: str = ""

    # RabbitMQ Queue/Exchange
    rabbitmq_queue_name: str = "document.process"
    rabbitmq_exchange_name: str = "minio-events"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator('rabbitmq_host', mode='after')
    @classmethod
    def normalize_rabbitmq_host(cls, v: str) -> str:
        """Normalize RabbitMQ host value"""
        # Handle empty or whitespace-only values
        if not v or v.strip() == "":
            logger.warning("RABBITMQ_HOST is empty, using 'localhost' as default")
            return "localhost"
        
        return v

    @model_validator(mode='after')
    def validate_and_build_urls(self):
        """Validate credentials and build database_url if not provided"""
        # Validate RabbitMQ credentials
        if not self.rabbitmq_user or not self.rabbitmq_password:
            raise ValueError("RABBITMQ_USER and RABBITMQ_PASSWORD are required")
        
        # Build database_url if not provided
        if not self.database_url:
            # URL-encode username and password to handle special characters
            encoded_user = quote_plus(self.postgres_user)
            encoded_password = quote_plus(self.postgres_password)
            self.database_url = (
                f"postgresql://{encoded_user}:{encoded_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        
        return self

    @property
    def postgres_dsn(self) -> str:
        """Returns the PostgreSQL DSN with URL-encoded credentials"""
        encoded_user = quote_plus(self.postgres_user)
        encoded_password = quote_plus(self.postgres_password)
        return (
            f"postgresql://{encoded_user}:{encoded_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def rabbitmq_url(self) -> str:
        """Returns the RabbitMQ connection URL with URL-encoded credentials"""
        # Use already-normalized host from normalize_rabbitmq_host validator
        encoded_user = quote_plus(self.rabbitmq_user)
        encoded_password = quote_plus(self.rabbitmq_password)
        url = f"amqp://{encoded_user}:{encoded_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        logger.debug(f"RabbitMQ URL: amqp://{encoded_user}:***@{self.rabbitmq_host}:{self.rabbitmq_port}/")
        return url


settings = Settings()

