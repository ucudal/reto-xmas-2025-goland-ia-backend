from typing import List

from langchain_core.documents import Document


def document_to_chunks(document: Document, chunk_size: int, chunk_overlap: int) -> List[Document]:
    """
    Placeholder function - to be implemented later.

    This function will:
    1. Split the LangChain Document into smaller chunks
    2. Use a text splitter (e.g., RecursiveCharacterTextSplitter) with the specified parameters
    3. Return a list of Document chunks

    Args:
        document: LangChain Document to be chunked
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks

    Returns:
        List[Document]: List of LangChain Document chunks

    Raises:
        NotImplementedError: This function is not yet implemented
    """
    raise NotImplementedError("This function will be implemented later")

