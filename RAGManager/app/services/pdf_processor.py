from langchain_core.documents import Document


def pdf_to_document(minio_url: str) -> Document:
    """
    Placeholder function - to be implemented later.

    This function will:
    1. Download the PDF file from MinIO using the provided URL
    2. Parse the PDF content
    3. Convert it to a LangChain Document object

    Args:
        minio_url: URL pointing to the PDF file in MinIO

    Returns:
        Document: LangChain Document object containing the PDF content

    Raises:
        NotImplementedError: This function is not yet implemented
    """
    raise NotImplementedError("This function will be implemented later")

