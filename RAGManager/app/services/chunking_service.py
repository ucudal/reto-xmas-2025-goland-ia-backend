"""Document chunking service with table-aware splitting."""

import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback values
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200

# Minimum size for a text chunk to stand alone; smaller chunks get merged with previous
MIN_STANDALONE_CHUNK_SIZE = 150


def document_to_chunks(
    documents: list[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """
    Split documents into chunks for embedding.

    Tables (content_type="table") are NEVER split - they remain atomic
    regardless of size. Only text blocks are chunked.

    Args:
        documents: List of Document objects (from pdf_to_document)
        chunk_size: Target size for TEXT chunks (tables ignore this)
        chunk_overlap: Overlap for text chunks

    Returns:
        List of chunked Documents
    """
    # Resolve chunk_size with fallback chain: parameter -> settings -> default
    if chunk_size is None:
        chunk_size = getattr(settings, "chunk_size", None)
    if not chunk_size or chunk_size <= 0:
        chunk_size = DEFAULT_CHUNK_SIZE

    # Resolve chunk_overlap with fallback chain: parameter -> settings -> default
    if chunk_overlap is None:
        chunk_overlap = getattr(settings, "chunk_overlap", None)
    if chunk_overlap is None or chunk_overlap < 0:
        chunk_overlap = DEFAULT_CHUNK_OVERLAP

    # Ensure overlap doesn't exceed chunk size
    if chunk_overlap >= chunk_size:
        chunk_overlap = chunk_size // 5

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
        separators=["\n\n", "\n", " "],
    )

    result_chunks: list[Document] = []

    for doc in documents:
        content_type = doc.metadata.get("content_type", "text")

        if content_type == "table":
            # Tables are ATOMIC - never split
            # Add marker so we know this chunk is a complete table
            table_doc = Document(
                page_content=doc.page_content,
                metadata={
                    **doc.metadata,
                    "is_atomic": True,
                    "start_index": 0,
                },
            )
            result_chunks.append(table_doc)

            table_size = len(doc.page_content)
            if table_size > chunk_size:
                logger.debug(
                    "Table chunk exceeds target size (%d > %d) but kept atomic",
                    table_size,
                    chunk_size,
                )
        else:
            # Text blocks get chunked normally
            text_chunks = text_splitter.split_documents([doc])
            for chunk in text_chunks:
                chunk.metadata["is_atomic"] = False
                result_chunks.append(chunk)

    # Merge small chunks with the previous chunk to maintain context
    merged_chunks: list[Document] = []
    for chunk in result_chunks:
        chunk_size_actual = len(chunk.page_content)
        is_small = chunk_size_actual < MIN_STANDALONE_CHUNK_SIZE
        is_text = chunk.metadata.get("content_type", "text") == "text"

        if is_small and is_text and merged_chunks:
            # Append to previous chunk
            prev_chunk = merged_chunks[-1]
            merged_content = prev_chunk.page_content + "\n\n" + chunk.page_content
            merged_chunks[-1] = Document(
                page_content=merged_content,
                metadata={
                    **prev_chunk.metadata,
                    # Update to reflect merged content
                    "merged_small_chunk": True,
                },
            )
            logger.debug(
                "Merged small chunk (%d chars) with previous chunk",
                chunk_size_actual,
            )
        else:
            merged_chunks.append(chunk)

    return merged_chunks

