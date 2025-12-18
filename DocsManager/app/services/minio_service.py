from minio import Minio
from minio.error import S3Error
from io import BytesIO
import logging
from typing import Optional
from app.core.config import settings
import uuid
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class MinIOService:
    """Service to interact with MinIO"""

    def __init__(self):
        # Parse endpoint to extract host and port
        # Handle both URL format (http://host:port) and simple format (host:port)
        endpoint_str = settings.minio_endpoint.strip()
        
        # If it starts with http:// or https://, parse as URL
        if endpoint_str.startswith(('http://', 'https://')):
            parsed = urlparse(endpoint_str)
            endpoint = parsed.netloc
        else:
            # Simple format: host:port or just host
            endpoint = endpoint_str
        
        # Validate that the endpoint is not empty
        if not endpoint or endpoint.strip() == "":
            error_msg = (
                f"Invalid MinIO endpoint configuration: '{settings.minio_endpoint}'. "
                "Endpoint must be a valid host or host:port (e.g., 'localhost:9000' or 'minio:9000')"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        self.client = Minio(
            endpoint=endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
        self.bucket_name = settings.minio_bucket
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Verifies that the bucket exists, creates it if it doesn't"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket '{self.bucket_name}' created")
            else:
                logger.info(f"Bucket '{self.bucket_name}' already exists")
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error ensuring bucket exists: {e}")
            raise

    def upload_file(self, file_data: bytes, filename: str, content_type: str = "application/pdf") -> str:
        """
        Uploads a file to MinIO

        Args:
            file_data: File content in bytes
            filename: Original filename
            content_type: MIME type of the file

        Returns:
            File path in MinIO (object_name)
        """
        try:
            # Generate a unique name for the file
            file_extension = filename.split(".")[-1] if "." in filename else "pdf"
            # Use MINIO_FOLDER to organize files in a specific folder
            folder = settings.minio_folder.rstrip("/")  # Remove trailing slash if present
            object_name = f"{folder}/{uuid.uuid4()}.{file_extension}"

            file_stream = BytesIO(file_data)
            file_size = len(file_data)

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_stream,
                length=file_size,
                content_type=content_type,
            )

            logger.info(f"File uploaded to MinIO: {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"Error uploading file to MinIO: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading file to MinIO: {e}")
            raise

    def download_file(self, object_name: str) -> bytes:
        """
        Downloads a file from MinIO

        Args:
            object_name: Object name in MinIO

        Returns:
            File content in bytes
        """
        try:
            response = self.client.get_object(bucket_name=self.bucket_name, object_name=object_name)
            file_data = response.read()
            logger.info(f"File downloaded from MinIO: {object_name}")
            return file_data
        except S3Error as e:
            logger.error(f"Error downloading file from MinIO: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading file from MinIO: {e}")
            raise
        finally:
            if "response" in locals() and response:
                response.close()
                response.release_conn()

    def delete_file(self, object_name: str):
        """
        Deletes a file from MinIO

        Args:
            object_name: Object name in MinIO
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"File '{object_name}' deleted from MinIO")
        except S3Error as e:
            logger.error(f"Error deleting file from MinIO: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting file from MinIO: {e}")
            raise


# Global instance
minio_service = MinIOService()

