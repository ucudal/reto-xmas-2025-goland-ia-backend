import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentListPaginatedResponse,
)
from app.core.db_connection import get_db
from app.models.document import Document as DocumentModel
from app.services.minio_service import minio_service
from app.core.rabbitmq import rabbitmq
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Validations
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf"}


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Endpoint to upload a PDF document (FastApi 1 - Gestión de documentos)

    Flow:
    1. Validate file
    2. Save to MinIO
    3. Save metadata to PostgreSQL
    4. Publish message to RabbitMQ
    5. Return immediate response
    """
    try:
        # 1. Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Validate extension
        file_extension = (
            "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
        )
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Read file content
        file_content = await file.read()

        # Validate size
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024)}MB",
            )

        # 2. Save to MinIO
        minio_path = minio_service.upload_file(
            file_data=file_content,
            filename=file.filename,
            content_type=file.content_type or "application/pdf",
        )

        # 3. Save metadata to PostgreSQL
        try:
            doc_model = DocumentModel(
                filename=file.filename,
                minio_path=minio_path,
                uploaded_at=datetime.utcnow(),
            )
            db.add(doc_model)
            db.commit()
            db.refresh(doc_model)
            document_id = doc_model.id

            if not document_id:
                # If it fails, delete the file from MinIO
                minio_service.delete_file(minio_path)
                raise HTTPException(status_code=500, detail="Failed to save document metadata")

        except Exception as e:
            # Clean up MinIO file on any database error
            try:
                minio_service.delete_file(minio_path)
                logger.info(f"Cleaned up MinIO file after DB error: {minio_path}")
            except Exception as delete_error:
                logger.error(f"Failed to delete MinIO file during cleanup: {delete_error}")
            
            # Rollback database transaction
            db.rollback()
            logger.error(f"Database error during document upload: {e}")
            
            # Re-raise as HTTPException if not already one
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save document metadata: {str(e)}"
            )

        # 4. Publish message to RabbitMQ (only after successful DB commit)
        message = {
            "document_id": document_id,
            "minio_path": minio_path,
            "filename": file.filename,
        }

        try:
            rabbitmq.publish_message(settings.queue_name, message)
        except Exception as e:
            logger.error(f"Failed to publish message to RabbitMQ: {e}")
            # Don't fail the request, but log the error
            # The document is already saved, it can be processed manually

        # 5. Return response
        return DocumentUploadResponse(
            id=document_id,
            filename=file.filename,
            status="processing",
            uploaded_at=doc_model.uploaded_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get metadata of a document"""
    doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        minio_path=doc.minio_path,
        uploaded_at=doc.uploaded_at,
    )


@router.get("", response_model=DocumentListPaginatedResponse)
async def list_documents(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List all documents with pagination
    
    Args:
        limit: Maximum number of documents to return (default: 10)
        offset: Number of documents to skip (default: 0)
        db: Database session
    
    Returns:
        Paginated list of documents with total count
    """
    # Get total count of documents
    total = db.query(DocumentModel).count()
    
    # Get paginated documents
    docs = (
        db.query(DocumentModel)
        .order_by(DocumentModel.uploaded_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return DocumentListPaginatedResponse(
        documents=[
            DocumentListResponse(
                id=doc.id,
                filename=doc.filename,
                uploaded_at=doc.uploaded_at,
            )
            for doc in docs
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document from both PostgreSQL and MinIO"""
    try:
        # 1. Get document info from database
        doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        minio_path = doc.minio_path

        # 2. Delete from database first (inside transaction)
        try:
            # Delete chunks associated with the document (cascade will handle this)
            db.delete(doc)
            db.commit()
            logger.info(f"Document {document_id} deleted from database")
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting document {document_id} from database: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete document from database: {str(e)}"
            )

        # 3. Delete from MinIO as best-effort (after DB commit)
        try:
            minio_service.delete_file(minio_path)
            logger.info(f"Deleted file from MinIO: {minio_path}")
        except Exception as e:
            logger.warning(
                f"Failed to delete file from MinIO (file may not exist): {e}"
            )
            # Do not rollback DB or raise error - MinIO cleanup is best-effort

        logger.info(f"Document {document_id} deleted successfully")
        return {"message": "Document deleted successfully", "document_id": document_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

