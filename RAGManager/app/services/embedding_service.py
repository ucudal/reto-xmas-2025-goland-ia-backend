from typing import List, Tuple

from langchain_core.documents import Document


def chunks_to_embeddings(chunks: List[Document]) -> List[Tuple[str, List[float]]]:
    """
    Placeholder function - to be implemented later.

    This function will:
    1. Generate embeddings for each chunk using OpenAI's embedding API
    2. Return a list of tuples containing chunk content and its embedding vector

    Args:
        chunks: List of LangChain Document chunks to embed

    Returns:
        List[Tuple[str, List[float]]]: List of tuples containing (content, embedding_vector)
        where embedding_vector is a list of floats with dimension 1536

    Raises:
        NotImplementedError: This function is not yet implemented
    """
    raise NotImplementedError("This function will be implemented later")

