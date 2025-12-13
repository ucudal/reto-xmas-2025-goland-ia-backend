import io
import pdfplumber
from langchain_core.documents import Document
from minio import Minio

from app.core.config import settings



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

    documents: list[Document] = []
    
    # Download the PDF from MinIO into memory
    response = minio_client.get_object(bucket_name, object_name)
    try:
        pdf_bytes = response.read()
    finally:
        response.close()
        response.release_conn()

    # Open PDF from bytes using pdfplumber
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""

            # Extract tables and convert to text format
            tables = page.extract_tables()
            table_text = ""
            for table in tables:
                for row in table:
                    table_text += " | ".join(str(cell) if cell else "" for cell in row) + "\n"

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

