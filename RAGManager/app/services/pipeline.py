import logging
from datetime import datetime

from langchain_core.documents import Document

from app.core.config import settings
from app.core.database_connection import SessionLocal
from app.services.chunking_service import document_to_chunks
from app.services.embedding_service import chunks_to_embeddings
from app.services.pdf_processor import pdf_to_document
from app.models.document import Document as DocumentModel, DocumentChunk

logger = logging.getLogger(__name__)


def process_pdf_pipeline(minio_path: str, filename: str, document_id: int = None) -> int:
    """
    Orchestrates the PDF processing pipeline.

    This function coordinates the complete pipeline:
    1. PDF to LangChain Document
    2. Document to Chunks
    3. Chunks to Embeddings
    4. Store in database

    Args:
        minio_path: Object name/path in MinIO (not a full URL)
        filename: Original filename
        document_id: Optional document ID if document already exists in DB

    Returns:
        int: document_id of the created/updated document

    Raises:
        Exception: If any of the pipeline stages fail
    """
    logger.info(f"Starting PDF processing pipeline for: {minio_path}")

    db = SessionLocal()
    try:
        # Stage 1: PDF to Document
        logger.info("Stage 1: Converting PDF to LangChain Document")
        document = pdf_to_document(minio_path)
        logger.info("Stage 1 completed successfully")

        # Stage 2: Document to Chunks
        logger.info(
            f"Stage 2: Splitting document into chunks (size={settings.chunk_size}, overlap={settings.chunk_overlap})"
        )
        chunks = document_to_chunks(document, settings.chunk_size, settings.chunk_overlap)
        logger.info(f"Stage 2 completed successfully. Created {len(chunks)} chunks")

        # Stage 3: Chunks to Embeddings
        logger.info("Stage 3: Generating embeddings for chunks")
        embeddings_tuples = chunks_to_embeddings(chunks)
        logger.info(f"Stage 3 completed successfully. Generated {len(embeddings_tuples)} embeddings")

        # Stage 4: Store in database
        logger.info("Stage 4: Storing chunks and embeddings in database")

        # Get or create document record
        if document_id:
            doc_model = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
            if not doc_model:
                raise ValueError(f"Document with id {document_id} not found")
            # Delete existing chunks
            db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        else:
            # Create new document record
            doc_model = DocumentModel(
                filename=filename,
                minio_path=minio_path,
                uploaded_at=datetime.utcnow(),
            )
            db.add(doc_model)
            db.flush()  # Get the ID without committing
            document_id = doc_model.id

        # Create chunk records with embeddings
        chunk_models = []
        for i, (chunk_text, embedding) in enumerate(embeddings_tuples):
            chunk_model = DocumentChunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk_text,
                embedding=embedding,  # pgvector.sqlalchemy.Vector handles the conversion
                created_at=datetime.utcnow(),
            )
            chunk_models.append(chunk_model)

        db.bulk_save_objects(chunk_models)
        db.commit()

        logger.info(f"Stage 4 completed successfully. Saved {len(chunk_models)} chunks to database")
        logger.info(f"Pipeline completed with document_id: {document_id}")
        return document_id

    except Exception as e:
        db.rollback()
        logger.error(f"Error in PDF processing pipeline: {e}")
        raise
    finally:
        db.close()

