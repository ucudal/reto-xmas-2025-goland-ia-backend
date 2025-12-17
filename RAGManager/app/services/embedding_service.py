"""
DEPRECATED: This module is no longer used.

Embedding generation is now handled by the vector_store module using LangChain PGVector,
which generates embeddings internally when storing documents.

See: app/services/vector_store.py
"""

from typing import List, Tuple

from langchain_core.documents import Document


def chunks_to_embeddings(chunks: List[Document]) -> List[Tuple[str, List[float]]]:
    """
    DEPRECATED: Use vector_store.store_chunks_with_embeddings() instead.

    This function is no longer used. Embedding generation is now handled
    by LangChain PGVector's add_documents() method, which generates
    embeddings internally using OpenAI.

    Args:
        chunks: List of LangChain Document chunks to embed

    Returns:
        List[Tuple[str, List[float]]]: List of tuples containing (content, embedding_vector)
        where embedding_vector is a list of floats with dimension 1536

    Raises:
        DeprecationWarning: This function should not be used
    """
    raise DeprecationWarning(
        "This function is deprecated. Use vector_store.store_chunks_with_embeddings() instead."
    )

