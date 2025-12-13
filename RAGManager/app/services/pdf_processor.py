import pdfplumber
from io import BytesIO
from langchain_core.documents import Document
import logging
from app.services.minio_service import minio_service

logger = logging.getLogger(__name__)


def pdf_to_document(minio_path: str) -> Document:
    """
    Downloads a PDF from MinIO and converts it to a LangChain Document.

    Args:
        minio_path: Object name/path in MinIO (not a full URL)

    Returns:
        Document: LangChain Document object containing the PDF content

    Raises:
        ValueError: If no text is extracted from the PDF
        Exception: If there's an error downloading or processing the PDF
    """
    try:
        # Download PDF from MinIO
        logger.info(f"Downloading PDF from MinIO: {minio_path}")
        pdf_data = minio_service.download_file(minio_path)

        # Extract text from PDF
        pdf_file = BytesIO(pdf_data)
        text_parts = []

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        full_text = "\n\n".join(text_parts)

        if not full_text or len(full_text.strip()) == 0:
            raise ValueError("No text extracted from PDF")

        logger.info(f"Extracted {len(full_text)} characters from PDF")

        # Create LangChain Document
        document = Document(
            page_content=full_text,
            metadata={"source": minio_path, "type": "pdf"},
        )

        return document
    except Exception as e:
        logger.error(f"Error processing PDF from MinIO: {e}")
        raise

