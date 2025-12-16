from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def split_documents(documents):
    """
    Split a list of documents into smaller chunks.
    
    Args:
        documents: List of documents to split
        
    Returns:
        List of split documents (chunks)
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        add_start_index=True
    )
    
    all_splits = text_splitter.split_documents(documents)
    
    return all_splits


def document_to_chunks(document: Document, chunk_size: int, chunk_overlap: int):
    """
    Split a single document into smaller chunks with specified size and overlap.
    
    Args:
        document: LangChain Document to split
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of split documents (chunks)
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True
    )
    
    # Convert single document to list for split_documents
    chunks = text_splitter.split_documents([document])
    
    return chunks

