import logging
from fastapi import APIRouter, HTTPException

from app.schemas.document import ProcessPDFRequest, ProcessPDFResponse
from app.services.pipeline import process_pdf_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/process", response_model=ProcessPDFResponse)
async def process_pdf(request: ProcessPDFRequest) -> ProcessPDFResponse:
    """
    Process a PDF file from MinIO URL through the RAG pipeline (FastApi 2 - Gestión de RAG).

    This endpoint receives a MinIO URL, triggers the PDF processing pipeline,
    and returns the processing status. The pipeline includes:
    1. PDF to LangChain Document conversion
    2. Document chunking
    3. Embedding generation
    4. Database storage

    Args:
        request: ProcessPDFRequest containing the MinIO URL

    Returns:
        ProcessPDFResponse with processing status and document_id

    Raises:
        HTTPException: If validation fails or processing encounters an error
    """
    logger.info(f"Received PDF processing request for URL: {request.minio_url}")

    try:
        # Validate MinIO URL format (basic validation)
        if not request.minio_url or len(request.minio_url.strip()) == 0:
            raise HTTPException(status_code=400, detail="minio_url cannot be empty")

        # Extract minio_path from URL (assuming format: https://endpoint/bucket/path)
        # For now, we'll use the URL as-is and let pdf_processor handle it
        minio_path = request.minio_url.split("/")[-1]  # Simple extraction

        # Trigger the pipeline
        document_id = process_pdf_pipeline(minio_path=minio_path, filename=minio_path)

        return ProcessPDFResponse(
            status="success",
            document_id=document_id,
            message=f"PDF processing pipeline completed successfully. Document ID: {document_id}",
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
