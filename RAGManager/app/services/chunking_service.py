from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List
import logging
import time
from app.core.config import settings

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    Divides text into chunks with overlap.

    Args:
        text: Text to divide
        chunk_size: Approximate size of each chunk (in tokens/words). If None, uses config value.
        overlap: Number of words of overlap between chunks. If None, uses config value.

    Returns:
        List of text chunks
    """
    # Use config values if not provided
    if chunk_size is None:
        chunk_size = settings.chunk_size
    if overlap is None:
        overlap = settings.chunk_overlap

    start_time = time.time()

    # Split into words
    split_start = time.time()
    logger.debug(f"Splitting text into words...")
    words = text.split()
    split_time = time.time() - split_start
    logger.debug(f"Text split into words: {len(words)} words in {split_time:.2f}s")

    if len(words) <= chunk_size:
        logger.debug(f"Text is small ({len(words)} words), returning as single chunk")
        return [text]

    # Create chunks
    chunk_start = time.time()
    chunks = []
    start = 0
    chunk_count = 0
    max_chunks = (len(words) // (chunk_size - overlap)) + 10  # Reasonable max estimate
    previous_start = -1  # To detect infinite loops

    while start < len(words):
        # Protection against infinite loop
        if chunk_count > max_chunks:
            logger.error(f"Too many chunks ({chunk_count}), possible infinite loop. Breaking.")
            break

        if start == previous_start:
            logger.error(f"Infinite loop detected: start={start} not advancing. Breaking.")
            break

        previous_start = start

        # Calculate chunk end
        end = min(start + chunk_size, len(words))

        # Validate that end > start
        if end <= start:
            logger.error(f"Invalid chunk boundaries: start={start}, end={end}. Breaking.")
            break

        chunk_words = words[start:end]
        chunk = " ".join(chunk_words)

        # Only add chunks that have a reasonable minimum size
        # (at least half of chunk_size or more than overlap)
        min_chunk_size = max(overlap, chunk_size // 2)
        if len(chunk_words) >= min_chunk_size or end >= len(words):
            chunks.append(chunk)
            chunk_count += 1
        else:
            # If chunk is very small and not the end, skip it
            logger.debug(f"Skipping very small chunk at end: {len(chunk_words)} words")
            break

        # Log every 100 chunks to avoid saturating logs
        if chunk_count % 100 == 0:
            logger.debug(
                f"Created {chunk_count} chunks so far (start={start}, end={end}, remaining={len(words)-end} words)..."
            )

        # If we reached the end of text, finish
        if end >= len(words):
            break

        # Calculate next start with overlap
        new_start = end - overlap

        # If remaining text is very small, don't apply overlap
        # (avoids very small chunks at the end)
        remaining_words = len(words) - end
        if remaining_words < chunk_size:
            # If there are fewer words left than chunk_size
            if remaining_words <= overlap:
                # If very little left (less or equal to overlap), finish
                # (we already included the important part in the previous chunk with overlap)
                break
            else:
                # If more than overlap but less than chunk_size,
                # create a last chunk without overlap
                new_start = end

        # Validate that new start advances
        if new_start <= start:
            logger.warning(
                f"Overlap too large or chunk too small: start={start}, end={end}, new_start={new_start}. Adjusting..."
            )
            new_start = start + 1  # Force minimum advance

        start = new_start

    chunk_time = time.time() - chunk_start
    total_time = time.time() - start_time

    logger.info(
        f"Text divided into {len(chunks)} chunks in {total_time:.2f}s (split: {split_time:.2f}s, chunking: {chunk_time:.2f}s)"
    )
    return chunks


def document_to_chunks(document: Document, chunk_size: int = None, overlap: int = None) -> List[Document]:
    """
    Converts a LangChain Document into chunks using the custom chunking algorithm.

    Args:
        document: LangChain Document to split
        chunk_size: Size of each chunk in words. If None, uses config value.
        overlap: Overlap between chunks in words. If None, uses config value.

    Returns:
        List of LangChain Document chunks
    """
    # Extract text and chunk it
    text = document.page_content
    chunk_texts = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    # Convert chunks back to Document objects
    chunks = []
    for i, chunk_text in enumerate(chunk_texts):
        chunk_doc = Document(
            page_content=chunk_text,
            metadata={**document.metadata, "chunk_index": i},
        )
        chunks.append(chunk_doc)

    return chunks


def split_documents(documents: List[Document], chunk_size: int = None, overlap: int = None) -> List[Document]:
    """
    Split a list of documents into smaller chunks using the custom chunking algorithm.

    Args:
        documents: List of documents to split
        chunk_size: Size of each chunk in words. If None, uses config value.
        overlap: Overlap between chunks in words. If None, uses config value.

    Returns:
        List of split documents (chunks)
    """
    all_chunks = []
    for doc in documents:
        chunks = document_to_chunks(doc, chunk_size=chunk_size, overlap=overlap)
        all_chunks.extend(chunks)

    return all_chunks

