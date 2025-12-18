"""Nodo 5: Retriever - Performs semantic search in vector database."""

import logging
from typing import List
from urllib.parse import urlparse, urlunparse

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from app.agents.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(
    model=settings.embedding_model,
    openai_api_key=settings.openai_api_key,
)


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


def _get_vector_store() -> PGVector:
    """
    Get or create PGVector instance for document retrieval.

    Returns:
        PGVector instance configured with embeddings and connection
    """
    # Convert database URL to psycopg format required by langchain-postgres
    connection_string = _convert_database_url_to_psycopg(settings.database_url)

    # Collection name for the vector store
    # PGVector will use this to organize documents in its own schema
    collection_name = "document_chunks"

    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True,
    )

    return vector_store


def _retrieve_chunks_for_phrase(
    vector_store: PGVector, phrase: str, top_k: int = 3
) -> List[tuple[str, str]]:
    """
    Retrieve top-k most similar chunks for a given phrase using PGVector.

    Args:
        vector_store: PGVector instance
        phrase: Phrase to search for
        top_k: Number of top results to retrieve (default: 3)

    Returns:
        List of tuples (chunk_id, content) for the retrieved chunks
        chunk_id is extracted from document metadata if available, otherwise uses document index
    """
    # Use PGVector's similarity_search to find relevant chunks
    results = vector_store.similarity_search(phrase, k=top_k)

    chunks = []
    for idx, doc in enumerate(results):
        # Extract chunk ID from metadata if available, otherwise use index
        chunk_id = doc.metadata.get("id", str(idx))
        chunk_content = doc.page_content
        chunks.append((chunk_id, chunk_content))

    return chunks


def retriever(state: AgentState) -> AgentState:
    """
    Retriever node - Performs semantic search in vector database using LangChain PGVector.

    This node:
    1. Takes 3 paraphrased statements from parafraseo node
    2. For each statement, uses PGVector's similarity_search to query the database
    3. Retrieves top 3 most relevant chunks per statement
    4. Creates a unique union of all retrieved chunks (no duplicates)
    5. Stores the chunk contents in relevant_chunks

    Args:
        state: Agent state containing paraphrased_statements (list of 3 statements)

    Returns:
        Updated state with relevant_chunks set (list of unique chunk contents)
    """
    updated_state = state.copy()

    # Get the 3 paraphrased statements from state
    paraphrased_statements = state.get("paraphrased_statements")

    if not paraphrased_statements or len(paraphrased_statements) == 0:
        logger.warning(
            "No paraphrased statements found in state. Parafraseo node may not have been executed yet."
        )
        updated_state["relevant_chunks"] = []
        return updated_state

    # Ensure we have exactly 3 statements (or at least handle what we get)
    statements_to_process = (
        paraphrased_statements[:3] if len(paraphrased_statements) >= 3 else paraphrased_statements
    )
    logger.info(f"Retrieving documents for {len(statements_to_process)} statements")

    # Use a set to track unique chunk IDs to avoid duplicates
    seen_chunk_ids: set[str] = set()
    unique_chunks: List[str] = []

    try:
        # Get PGVector instance
        vector_store = _get_vector_store()

        # For each statement, retrieve top 3 chunks using PGVector's similarity_search
        for statement in statements_to_process:
            logger.debug(f"Retrieving chunks for statement: {statement[:50]}...")
            chunks = _retrieve_chunks_for_phrase(vector_store, statement, top_k=3)

            # Add chunks to unique list (avoiding duplicates by chunk ID)
            for chunk_id, chunk_content in chunks:
                if chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk_id)
                    unique_chunks.append(chunk_content)
                    logger.debug(f"Added chunk {chunk_id} to results")

        logger.info(f"Retrieved {len(unique_chunks)} unique chunks from {len(statements_to_process)} statements")
    except Exception as e:
        logger.error(f"Error during retrieval: {e}", exc_info=True)
        unique_chunks = []

    # Store the unique chunk contents in state
    updated_state["relevant_chunks"] = unique_chunks

    return updated_state