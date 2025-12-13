import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
)
from app.core.database_connection import get_db
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
    Handle an uploaded PDF: validate, store in object storage, save metadata, enqueue a processing message, and return the created document metadata.
    
    Parameters:
        file (UploadFile): The uploaded file. Must have a filename ending with `.pdf` and be no larger than 10 MB.
    
    Returns:
        DocumentUploadResponse: The stored document's id, filename, status set to "processing", and upload timestamp.
    
    Raises:
        HTTPException: 400 for validation errors (missing filename, disallowed extension, or file too large);
                       500 for failures saving metadata or other internal errors.
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

        # 4. Publish message to RabbitMQ
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
    """
    Retrieve metadata for a document by its ID.
    
    Parameters:
        document_id (int): ID of the document to retrieve.
    
    Returns:
        DocumentResponse: Contains `id`, `filename`, `minio_path`, and `uploaded_at`.
    
    Raises:
        HTTPException: with status 404 if the document is not found.
    """
    doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        minio_path=doc.minio_path,
        uploaded_at=doc.uploaded_at,
    )


@router.get("", response_model=list[DocumentListResponse])
async def list_documents(db: Session = Depends(get_db)):
    """
    Retrieve all documents ordered by upload time, newest first.
    
    Returns:
        A list of DocumentListResponse objects each containing `id`, `filename`, and `uploaded_at`, ordered newest first.
    """
    docs = db.query(DocumentModel).order_by(DocumentModel.uploaded_at.desc()).all()

    return [
        DocumentListResponse(
            id=doc.id,
            filename=doc.filename,
            uploaded_at=doc.uploaded_at,
        )
        for doc in docs
    ]


@router.delete("/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """
    Delete a document and its stored object.
    
    Deletes the document record from the database and attempts to remove the associated object from MinIO (MinIO deletion is best-effort and will not prevent database removal if the object is already missing).
    
    Returns:
        dict: Confirmation with keys `"message"` (success message) and `"document_id"` (the id of the deleted document).
    
    Raises:
        HTTPException: 404 if the document_id does not exist.
        HTTPException: 500 for other internal errors encountered during deletion.
    """
    try:
        # 1. Get document info from database
        doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        minio_path = doc.minio_path

        # 2. Delete from MinIO (if file exists)
        try:
            minio_service.delete_file(minio_path)
            logger.info(f"Deleted file from MinIO: {minio_path}")
        except Exception as e:
            logger.warning(
                f"File not found in MinIO (may have been deleted already): {e}"
            )
            # Continue with database deletion even if MinIO file doesn't exist

        # 3. Delete chunks associated with the document (cascade will handle this)
        # 4. Delete document from PostgreSQL
        db.delete(doc)
        db.commit()

        logger.info(f"Document {document_id} deleted successfully")
        return {"message": "Document deleted successfully", "document_id": document_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
