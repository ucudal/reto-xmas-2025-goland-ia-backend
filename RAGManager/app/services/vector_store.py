"""
Vector Store Service - Handles embedding generation and storage using LangChain PGVector.

This service provides functionality to:
1. Initialize PGVector connection with OpenAI embeddings
2. Store document chunks with their embeddings in batches
3. Convert database URLs to psycopg3 format required by langchain-postgres
"""

import logging
from urllib.parse import urlparse, urlunparse

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from app.core.config import settings

logger = logging.getLogger(__name__)

# Collection name for the vector store
COLLECTION_NAME = "document_chunks"

# Batch size for inserting documents (to handle large PDFs efficiently)
DEFAULT_BATCH_SIZE = 100


def _convert_database_url_to_psycopg(database_url: str) -> str:
    """
    Convert database URL to postgresql+psycopg format required by langchain-postgres.

    LangChain PGVector requires postgresql+psycopg:// (psycopg3) format.
    This function converts common formats (postgresql://, postgresql+psycopg2://) to the required format.

    Args:
        database_url: Original database URL

    Returns:
        Database URL in postgresql+psycopg:// format
    """
    parsed = urlparse(database_url)

    # Replace driver with psycopg (psycopg3)
    if parsed.scheme.startswith("postgresql"):
        # Remove any existing driver (e.g., +psycopg2)
        base_scheme = "postgresql"
        if "+" in parsed.scheme:
            base_scheme = parsed.scheme.split("+")[0]

        new_scheme = f"{base_scheme}+psycopg"
        new_parsed = parsed._replace(scheme=new_scheme)
        return urlunparse(new_parsed)

    return database_url


def _get_embeddings() -> OpenAIEmbeddings:
    """
    Get OpenAI embeddings instance configured from settings.

    Returns:
        OpenAIEmbeddings instance
    """
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )


def _get_vector_store() -> PGVector:
    """
    Get or create PGVector instance for document storage.

    Returns:
        PGVector instance configured with embeddings and connection
    """
    connection_string = _convert_database_url_to_psycopg(settings.database_url)
    embeddings = _get_embeddings()

    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=connection_string,
        use_jsonb=True,
    )

    return vector_store


def store_chunks_with_embeddings(
    filename: str,
    chunks: list[Document],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    """
    Store document chunks with their embeddings in PGVector.

    This function:
    1. Prepares chunks with metadata (document_id, chunk_index, filename)
    2. Uses LangChain PGVector to generate embeddings and store in batches
    3. Returns the number of chunks stored

    Args:
        document_id: ID of the parent document in the documents table
        filename: Original filename for metadata
        chunks: List of LangChain Document chunks to embed and store
        batch_size: Number of chunks to process per batch (default: 100)

    Returns:
        int: Number of chunks successfully stored

    Raises:
        Exception: If storage fails
    """
    if not chunks:
        logger.warning("No chunks provided for storage")
        return 0

    logger.info(f"Storing {len(chunks)} chunks")

    # Prepare documents with metadata for PGVector
    prepared_docs = []
    for idx, chunk in enumerate(chunks):
        # Create a new document with enriched metadata
        metadata = {
            "chunk_index": idx,
            "filename": filename,
            # Preserve any existing metadata from chunking
            **chunk.metadata,
        }
        prepared_docs.append(
            Document(
                page_content=chunk.page_content,
                metadata=metadata,
            )
        )

    # Get vector store instance
    vector_store = _get_vector_store()

    # Store documents in batches
    total_stored = 0
    for i in range(0, len(prepared_docs), batch_size):
        batch = prepared_docs[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(prepared_docs) + batch_size - 1) // batch_size

        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")

        try:
            # PGVector.add_documents handles embedding generation internally
            vector_store.add_documents(batch)
            total_stored += len(batch)
            logger.debug(f"Batch {batch_num} stored successfully")
        except Exception as e:
            logger.error(f"Error storing batch {batch_num}: {e}")
            raise

    logger.info(f"Successfully stored {total_stored} chunks")
    return total_stored
