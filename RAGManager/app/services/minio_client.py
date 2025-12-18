# MinIO client configuration and utilities.

import logging

import certifi
import urllib3
from minio import Minio
from urllib3.util import Timeout as UrllibTimeout

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_minio_client() -> Minio:
    """Create a MinIO client with proper timeout and retry configuration."""
    # Configure timeout: 10s connect, 30s read
    timeout = UrllibTimeout(connect=10, read=30)

    # Configure retry: 3 attempts with backoff for server errors
    retry = urllib3.Retry(
        total=3,
        backoff_factor=0.2,
        status_forcelist=[500, 502, 503, 504],
    )

    # Create PoolManager with timeout, retry, and CA bundle
    http_client = urllib3.PoolManager(
        timeout=timeout,
        retries=retry,
        maxsize=10,
        cert_reqs="CERT_REQUIRED",
        ca_certs=certifi.where(),
    )

    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        http_client=http_client,
    )


def download_object(
    object_name: str,
    bucket_name: str | None = None,
    minio_client: Minio | None = None,
) -> bytes:
    """
    Download an object from MinIO and return its content as bytes.

    Args:
        object_name: Path/name of the object in the bucket
        bucket_name: Name of the MinIO bucket (defaults to settings.minio_bucket)
        minio_client: Optional MinIO client (creates one if not provided)

    Returns:
        bytes: The object content

    Raises:
        ValueError: If object_name is empty or download fails
    """
    if bucket_name is None:
        bucket_name = settings.minio_bucket
    if minio_client is None:
        minio_client = get_minio_client()

    # Validate object_name
    if not object_name or not object_name.strip():
        raise ValueError("object_name cannot be empty or whitespace")

    # Download the object from MinIO into memory
    # Note: For very large files, consider streaming to disk instead of loading entirely into memory
    try:
        response = minio_client.get_object(bucket_name, object_name)
    except Exception as e:
        logger.error(
            "Failed to get object from MinIO - bucket: '%s', object: '%s': %s",
            bucket_name,
            object_name,
            e,
        )
        raise ValueError(
            f"Failed to retrieve '{object_name}' from bucket '{bucket_name}': {e}"
        ) from e

    try:
        content = response.read()
        # Warn if file is very large (e.g., > 100MB)
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > 100:
            logger.warning(
                "Large file loaded into memory: %.1f MB for '%s'",
                file_size_mb,
                object_name,
            )
        return content
    except Exception as e:
        logger.error(
            "Failed to read content from MinIO - bucket: '%s', object: '%s': %s",
            bucket_name,
            object_name,
            e,
        )
        raise ValueError(
            f"Failed to read content of '{object_name}' from bucket '{bucket_name}': {e}"
        ) from e
    finally:
        response.close()
        response.release_conn()
