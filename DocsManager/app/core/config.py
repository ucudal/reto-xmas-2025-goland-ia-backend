from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator, Field
from typing import Optional
from urllib.parse import quote_plus
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # PostgreSQL Configuration
    postgres_user: str = Field(..., env="DB_USER")
    postgres_password: str = Field(..., env="DB_PASSWORD")
    postgres_db: str = Field(..., env="DB_NAME")
    postgres_host: str = Field("localhost", env="DB_HOST")
    postgres_port: int = Field(5432, env="DB_PORT")

    # RabbitMQ Configuration
    rabbitmq_user: str = Field(..., env="RABBITMQ_USER")
    rabbitmq_password: str = Field(..., env="RABBITMQ_PASSWORD")
    rabbitmq_host: str = Field("localhost", env="RABBITMQ_HOST")
    rabbitmq_port: int = Field(5672, env="RABBITMQ_PORT")
    rabbitmq_management_port: int = Field(15672, env="RABBITMQ_MANAGEMENT_PORT")

    # MinIO Configuration
    minio_endpoint: str = Field(..., env="MINIO_ENDPOINT")
    minio_access_key: str = Field(..., env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(..., env="MINIO_SECRET_KEY")
    minio_bucket: str = Field("documents", env="MINIO_BUCKET")
    minio_use_ssl: bool = Field(True, env="MINIO_SECURE")

    # Database Configuration (for SQLAlchemy)
    database_url: str = Field("", env="DATABASE_URL")

    # RabbitMQ Queue/Exchange
    rabbitmq_queue_name: str = "document.process"
    rabbitmq_exchange_name: str = "minio-events"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="",
        env_map={
            "postgres_user": "DB_USER",
            "postgres_password": "DB_PASSWORD",
            "postgres_db": "DB_NAME",
        }
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

