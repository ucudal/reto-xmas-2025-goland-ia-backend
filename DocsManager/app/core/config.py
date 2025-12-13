from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
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

    # Database Configuration (for SQLAlchemy)
    database_url: str = ""

    # Application
    queue_name: str = "document.process"

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
        
        # Replace Docker service name with localhost
        if v.strip() == "rabbitmq":
            logger.warning(
                "RABBITMQ_HOST='rabbitmq' detected. Changing to 'localhost' because app runs outside Docker"
            )
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
            self.database_url = (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        
        return self

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
        host = self.rabbitmq_host.strip() if self.rabbitmq_host else "localhost"
        url = f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{host}:{self.rabbitmq_port}/"
        logger.debug(f"RabbitMQ URL: amqp://{self.rabbitmq_user}:***@{host}:{self.rabbitmq_port}/")
        return url


settings = Settings()

