import logging

from app.core.config import settings
from app.core.database_connection import SessionLocal
from app.models.document import Document
from app.services.chunking_service import document_to_chunks
from app.services.pdf_processor import pdf_to_document
from app.services.vector_store import store_chunks_with_embeddings

logger = logging.getLogger(__name__)


def _create_document_record(filename: str, minio_path: str) -> int:
    """
    Create a Document record in the database.

    Args:
        filename: Original filename of the PDF
        minio_path: Path to the PDF in MinIO bucket

    Returns:
        int: The created document's ID
    """
    db = SessionLocal()
    try:
        document = Document(filename=filename, minio_path=minio_path)
        db.add(document)
        db.commit()
        db.refresh(document)
        logger.info(f"Created document record with id={document.id}")
        return document.id
    finally:
        db.close()


def process_pdf_pipeline(object_name: str) -> int:
    """
    Orchestrates the PDF processing pipeline.

    This function coordinates the three-stage pipeline:
    1. PDF to LangChain Document
    2. Document to Chunks
    3. Embed and Store in database using PGVector

    Args:
        object_name: Path/name of the PDF object in the MinIO bucket

    Returns:
        int: document_id of the created document

    Raises:
        Exception: If any of the pipeline stages fail
    """
    logger.info(f"Starting PDF processing pipeline for object: {object_name}")

    try:
        # Stage 1: PDF to Document
        logger.info("Stage 1: Converting PDF to LangChain Document")
        document = pdf_to_document(object_name)
        logger.info("Stage 1 completed successfully")

        # Stage 2: Document to Chunks
        logger.info(
            f"Stage 2: Splitting document into chunks (size={settings.chunk_size}, overlap={settings.chunk_overlap})"
        )
        chunks = document_to_chunks(document, settings.chunk_size, settings.chunk_overlap)
        logger.info(f"Stage 2 completed successfully. Created {len(chunks)} chunks")

        # Stage 3: Embed and Store in database
        # First, create the document record to get the document_id
        logger.info("Stage 3: Embedding and storing chunks in database")

        # Extract filename from object_name (e.g., "folder/file.pdf" -> "file.pdf")
        filename = object_name.split("/")[-1] if "/" in object_name else object_name

        # Create document record in the documents table
        document_id = _create_document_record(filename=filename, minio_path=object_name)

        # Store chunks with embeddings using PGVector
        # This generates embeddings via OpenAI and stores in the vector database
        chunks_stored = store_chunks_with_embeddings(
            document_id=document_id,
            filename=filename,
            chunks=chunks,
        )
        logger.info(f"Stage 3 completed successfully. Stored {chunks_stored} chunks with embeddings")

        logger.info(f"Pipeline completed successfully. Document ID: {document_id}")
        return document_id

    except Exception as e:
        logger.error(f"Error in PDF processing pipeline: {e}")
        raise

