from langchain.text_splitter import RecursiveCharacterTextSplitter


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

