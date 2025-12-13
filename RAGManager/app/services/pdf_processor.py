import io
import logging

import pdfplumber
from langchain_core.documents import Document
from minio import Minio

from app.core.config import settings

logger = logging.getLogger(__name__)


def _sanitize_cell(cell) -> str:
    """Safely convert a cell value to string."""
    if cell is None:
        return ""
    if isinstance(cell, (str, int, float, bool)):
        return str(cell)
    try:
        return str(cell)
    except Exception:
        try:
            return repr(cell)
        except Exception:
            return ""


def _extract_tables_safely(page, page_num: int) -> str:
    """Extract tables from a page with robust error handling."""
    table_text = ""
    try:
        tables = page.extract_tables()
        if not isinstance(tables, (list, tuple)):
            logger.warning(f"Page {page_num}: extract_tables() returned non-iterable type {type(tables)}, skipping tables")
            return ""

        for table_idx, table in enumerate(tables):
            if not isinstance(table, (list, tuple)):
                logger.warning(f"Page {page_num}, Table {table_idx}: table is not iterable, skipping")
                continue

            for row_idx, row in enumerate(table):
                try:
                    if not isinstance(row, (list, tuple)):
                        logger.warning(f"Page {page_num}, Table {table_idx}, Row {row_idx}: row is not iterable, skipping")
                        continue
                    table_text += " | ".join(_sanitize_cell(cell) for cell in row) + "\n"
                except Exception as e:
                    logger.warning(f"Page {page_num}, Table {table_idx}, Row {row_idx}: error processing row: {e}")
                    continue

    except Exception as e:
        logger.warning(f"Page {page_num}: error extracting tables: {e}")

    return table_text


def get_minio_client() -> Minio:
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )

def pdf_to_document(
    object_name: str,
    bucket_name: str | None = None,
    minio_client: Minio | None = None,
) -> list[Document]:
    """
    Load a PDF file from MinIO and return a list of Document objects.
    Each page becomes a separate Document with metadata.

    Args:
        object_name: Path/name of the PDF object in the bucket
        bucket_name: Name of the MinIO bucket (defaults to settings.minio_bucket)
        minio_client: Optional MinIO client (creates one if not provided)

    Returns:
        List of Document objects, one per page
    """
    if bucket_name is None:
        bucket_name = settings.minio_bucket
    if minio_client is None:
        minio_client = get_minio_client()

    # Validate object_name
    if not object_name or not object_name.strip():
        raise ValueError("object_name cannot be empty or whitespace")

    documents: list[Document] = []

    # Download the PDF from MinIO into memory
    # Note: For very large files, consider streaming to disk instead of loading entirely into memory
    try:
        response = minio_client.get_object(bucket_name, object_name)
    except Exception as e:
        logger.error(f"Failed to get object from MinIO - bucket: '{bucket_name}', object: '{object_name}': {e}")
        raise ValueError(f"Failed to retrieve '{object_name}' from bucket '{bucket_name}': {e}") from e

    try:
        pdf_bytes = response.read()
        # Optional: warn if file is very large (e.g., > 100MB)
        file_size_mb = len(pdf_bytes) / (1024 * 1024)
        if file_size_mb > 100:
            logger.warning(f"Large PDF loaded into memory: {file_size_mb:.1f} MB for '{object_name}'")
    except Exception as e:
        logger.error(f"Failed to read PDF content from MinIO - bucket: '{bucket_name}', object: '{object_name}': {e}")
        raise ValueError(f"Failed to read content of '{object_name}' from bucket '{bucket_name}': {e}") from e
    finally:
        response.close()
        response.release_conn()

    # Open PDF from bytes using pdfplumber
    try:
        pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
    except Exception as e:
        logger.error(f"Failed to open PDF '{object_name}': {e} (possibly corrupted or password-protected)")
        return documents

    try:
        for page_num, page in enumerate(pdf.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as e:
                logger.warning(f"Page {page_num}: error extracting text: {e}")
                text = ""

            # Extract tables and convert to text format
            table_text = _extract_tables_safely(page, page_num)

            # Combine text and tables
            full_content = text
            if table_text:
                full_content += f"\n\n[Tables]\n{table_text}"

            doc = Document(
                page_content=full_content,
                metadata={
                    "source": f"minio://{bucket_name}/{object_name}",
                    "bucket": bucket_name,
                    "object_name": object_name,
                    "page": page_num,
                    "total_pages": len(pdf.pages),
                    "filename": object_name.split("/")[-1],
                },
            )
            documents.append(doc)
    finally:
        pdf.close()

    return documents

def pdf_to_single_document(
    object_name: str,
    bucket_name: str | None = None,
    minio_client: Minio | None = None,
) -> Document:
    """
    Load a PDF file from MinIO and return a single Document with all pages combined.

    Args:
        object_name: Path/name of the PDF object in the bucket
        bucket_name: Name of the MinIO bucket (defaults to settings.minio_bucket)
        minio_client: Optional MinIO client (creates one if not provided)

    Returns:
        Single Document object with all content
    """
    if bucket_name is None:
        bucket_name = settings.minio_bucket
    documents = pdf_to_document(object_name, bucket_name, minio_client)

    combined_content = "\n\n".join(doc.page_content for doc in documents)

    return Document(
        page_content=combined_content,
        metadata={
            "source": f"minio://{bucket_name}/{object_name}",
            "bucket": bucket_name,
            "object_name": object_name,
            "filename": object_name.split("/")[-1],
            "total_pages": len(documents),
        },
    )

