import logging
import mimetypes
import base64
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import false
from sqlalchemy.orm import Session
from minio.error import S3Error

import mimetypes
import tempfile
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from minio.error import S3Error

from fastapi.responses import StreamingResponse
from fastapi import Query


from app.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentListPaginatedResponse,
)
from app.core.db_connection import get_db
from app.models.document import Document as DocumentModel
from app.services.minio_service import minio_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


def extract_object_path_from_minio_path(minio_path: str) -> str:
    """
    Extract the actual MinIO object path from minio_path.
    Handles cases where minio_path might be a URL instead of a direct path.
    
    Args:
        minio_path: The minio_path from database (could be a path or URL)
    
    Returns:
        The actual object path to use with MinIO client
    """
    # If it's already a valid path (doesn't start with http:// or https://), return as is
    if not minio_path.startswith(('http://', 'https://')):
        return minio_path
    
    # It's a URL, try to extract the object path
    logger.warning(f"minio_path appears to be a URL, attempting to extract object path: {minio_path[:100]}...")
    
    try:
        parsed_url = urlparse(minio_path)
        
        # Check if it's a MinIO presigned URL or shared object URL
        # Format: http://host:port/api/v1/download-shared-object/{base64_encoded_url}
        if '/download-shared-object/' in parsed_url.path:
            # Extract the base64 encoded part
            encoded_part = parsed_url.path.split('/download-shared-object/')[-1]
            # Remove query parameters if any
            encoded_part = encoded_part.split('?')[0]
            
            logger.info(f"Attempting to decode base64: {encoded_part[:50]}...")
            
            try:
                # Decode base64 - handle padding issues
                # Add padding if needed (base64 strings should be multiples of 4)
                missing_padding = len(encoded_part) % 4
                if missing_padding:
                    encoded_part += '=' * (4 - missing_padding)
                
                decoded = base64.b64decode(encoded_part).decode('utf-8')
                logger.info(f"Decoded URL: {decoded}")
                
                # Parse the decoded URL to get the object path
                decoded_url = urlparse(decoded)
                logger.info(f"Parsed decoded URL - path: {decoded_url.path}")
                
                # Extract object path (everything after bucket name)
                # Format: http://host:port/bucket-name/object-path
                path_parts = decoded_url.path.strip('/').split('/', 1)  # Split into ['bucket-name', 'object-path']
                if len(path_parts) >= 2:
                    object_path = path_parts[1]  # Get everything after bucket name
                    logger.info(f"Extracted object path from URL: {object_path}")
                    return object_path
                elif len(path_parts) == 1:
                    # Only bucket name, no object path (shouldn't happen but handle it)
                    logger.warning(f"Only bucket name found in decoded URL: {path_parts[0]}")
            except Exception as e:
                logger.error(f"Failed to decode base64 from URL: {e}", exc_info=True)
        
        # Try to extract from query parameters (some presigned URLs have the object in query params)
        query_params = parse_qs(parsed_url.query)
        if 'key' in query_params:
            return unquote(query_params['key'][0])
        if 'object' in query_params:
            return unquote(query_params['object'][0])
        
        # Try to extract from path (e.g., /bucket-name/object-path)
        path_parts = parsed_url.path.strip('/').split('/', 1)
        if len(path_parts) >= 2:
            # Skip bucket name, return object path
            object_path = path_parts[1]
            logger.info(f"Extracted object path from URL path: {object_path}")
            return object_path
        
    except Exception as e:
        logger.error(f"Error extracting object path from URL: {e}")
    
    # If we can't extract it, raise an error
    raise ValueError(
        f"minio_path appears to be a URL but could not extract object path. "
        f"Please ensure minio_path contains the actual object path (e.g., 'rag-docs/uuid.pdf'), "
        f"not a URL. Current value: {minio_path[:200]}"
    )

# Validations
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf"}


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Endpoint to upload a PDF document (FastApi 1 - Gestión de documentos)

    Flow:
    1. Validate file
    2. Save to MinIO (in the folder specified by MINIO_FOLDER)
    3. Save metadata to PostgreSQL
    4. Return immediate response
    
    Note: MinIO events will automatically publish a message to RabbitMQ
    when a file is created in the configured folder.
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

        # 4. Return response
        # Note: MinIO events will automatically publish a message to RabbitMQ
        # when the file is created in the configured folder
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


@router.get("/{document_id}/docs")
async def view_file(
    document_id: int,
    db: Session = Depends(get_db)
):
    # 1️⃣ Buscar documento
    doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # 2️⃣ Extraer path real del objeto en MinIO
    try:
        object_path = extract_object_path_from_minio_path(doc.minio_path)
        if not object_path or object_path.startswith(("http://", "https://")):
            raise ValueError("minio_path inválido")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error procesando minio_path: {str(e)}"
        )

    # 3️⃣ Verificar existencia en MinIO
    try:
        minio_service.client.stat_object(
            minio_service.bucket_name,
            object_path
        )
    except S3Error:
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado en MinIO"
        )

    # 4️⃣ Obtener objeto desde MinIO
    try:
        obj = minio_service.client.get_object(
            minio_service.bucket_name,
            object_path
        )
    except S3Error:
        raise HTTPException(
            status_code=404,
            detail="Error al obtener archivo desde MinIO"
        )

    # 5️⃣ Detectar Content-Type
    content_type, _ = mimetypes.guess_type(doc.filename)
    if not content_type:
        content_type = "application/octet-stream"

    return StreamingResponse(
    obj,
    media_type=content_type,
    headers={
        "Content-Disposition": f'attachment; filename="{doc.filename}"'
    }
)


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

