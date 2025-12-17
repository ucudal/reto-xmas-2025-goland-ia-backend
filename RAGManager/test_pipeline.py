"""
Test script to verify PDF processing, chunking, and vector storage work together.

Usage:
    1. Fill in the OBJECT_NAME with a PDF file from your MinIO bucket
    2. Run inside container: docker compose exec rag-manager uv run python test_pipeline.py
    3. Or locally: cd RAGManager && uv run python test_pipeline.py
"""

import json
import logging
from pathlib import Path

from app.services.pdf_processor import pdf_to_document
from app.services.chunking_service import document_to_chunks
from app.services.vector_store import store_chunks_with_embeddings, _get_vector_store
from app.core.database_connection import SessionLocal
from app.models.document import Document

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================
# FILL IN YOUR OBJECT NAME HERE
# ============================================================
OBJECT_NAME = "AK3079.pdf"  # e.g., "bd0662ac-479e-4da2-ad95-f6f335ac7e9e.pdf"
# ============================================================

# Output files
DUMP_DIR = Path(__file__).parent
DOCUMENTS_DUMP = DUMP_DIR / "dump_documents.txt"
CHUNKS_DUMP = DUMP_DIR / "dump_chunks.txt"
METADATA_DUMP = DUMP_DIR / "dump_metadata.json"


def write_documents_dump(documents):
    """Write all extracted documents to a dump file."""
    with open(DOCUMENTS_DUMP, "w", encoding="utf-8") as f:
        f.write(f"{'=' * 80}\n")
        f.write(f"EXTRACTED DOCUMENTS FROM: {OBJECT_NAME}\n")
        f.write(f"Total pages: {len(documents)}\n")
        f.write(f"{'=' * 80}\n\n")

        for i, doc in enumerate(documents):
            f.write(f"\n{'─' * 80}\n")
            f.write(f"PAGE {i + 1}\n")
            f.write(f"Metadata: {doc.metadata}\n")
            f.write(f"{'─' * 80}\n\n")
            f.write(doc.page_content)
            f.write("\n")

    logger.info(f"📄 Documents written to: {DOCUMENTS_DUMP}")


def write_chunks_dump(chunks):
    """Write all chunks to a dump file."""
    with open(CHUNKS_DUMP, "w", encoding="utf-8") as f:
        f.write(f"{'=' * 80}\n")
        f.write(f"CHUNKS FROM: {OBJECT_NAME}\n")
        f.write(f"Total chunks: {len(chunks)}\n")
        f.write(f"{'=' * 80}\n\n")

        for i, chunk in enumerate(chunks):
            f.write(f"\n{'─' * 80}\n")
            f.write(f"CHUNK {i + 1} (length: {len(chunk.page_content)})\n")
            f.write(f"Metadata: {chunk.metadata}\n")
            f.write(f"{'─' * 80}\n\n")
            f.write(chunk.page_content)
            f.write("\n")

    logger.info(f"📄 Chunks written to: {CHUNKS_DUMP}")


def write_metadata_dump(documents, chunks):
    """Write metadata summary as JSON."""
    chunk_sizes = [len(c.page_content) for c in chunks]

    metadata = {
        "object_name": OBJECT_NAME,
        "total_pages": len(documents),
        "total_chunks": len(chunks),
        "chunk_stats": {
            "min_size": min(chunk_sizes) if chunk_sizes else 0,
            "max_size": max(chunk_sizes) if chunk_sizes else 0,
            "avg_size": sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
        },
        "documents": [
            {
                "page": doc.metadata.get("page"),
                "content_length": len(doc.page_content),
                "metadata": doc.metadata,
            }
            for doc in documents
        ],
        "chunks": [
            {
                "index": i + 1,
                "content_length": len(chunk.page_content),
                "metadata": chunk.metadata,
            }
            for i, chunk in enumerate(chunks)
        ],
    }

    with open(METADATA_DUMP, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)

    logger.info(f"📄 Metadata written to: {METADATA_DUMP}")


def create_document_record(filename: str, minio_path: str) -> int:
    """Create a Document record in the database and return its ID."""
    db = SessionLocal()
    try:
        document = Document(filename=filename, minio_path=minio_path)
        db.add(document)
        db.commit()
        db.refresh(document)
        logger.info(f"✓ Created document record with id={document.id}")
        return document.id
    finally:
        db.close()


def main():
    logger.info(f"Starting test with object: {OBJECT_NAME}")

    # Stage 1: PDF to Documents
    logger.info("=" * 50)
    logger.info("Stage 1: Converting PDF to Documents")
    logger.info("=" * 50)

    try:
        documents = pdf_to_document(OBJECT_NAME)
        logger.info(f"✓ Extracted {len(documents)} pages from PDF")
        write_documents_dump(documents)

    except Exception as e:
        logger.error(f"✗ Failed to process PDF: {e}")
        return

    # Stage 2: Documents to Chunks
    logger.info("")
    logger.info("=" * 50)
    logger.info("Stage 2: Splitting Documents into Chunks")
    logger.info("=" * 50)

    try:
        chunks = document_to_chunks(documents)
        logger.info(f"✓ Created {len(chunks)} chunks from {len(documents)} pages")

        chunk_sizes = [len(chunk.page_content) for chunk in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
        logger.info(f"  Chunk sizes: min={min(chunk_sizes)}, max={max(chunk_sizes)}, avg={avg_size:.0f}")

        write_chunks_dump(chunks)
        write_metadata_dump(documents, chunks)

    except Exception as e:
        logger.error(f"✗ Failed to chunk documents: {e}")
        return

    # Stage 3: Embed and Store in Vector Database
    logger.info("")
    logger.info("=" * 50)
    logger.info("Stage 3: Embedding and Storing in PGVector")
    logger.info("=" * 50)

    try:
        # Create document record first
        filename = OBJECT_NAME.split("/")[-1] if "/" in OBJECT_NAME else OBJECT_NAME
        document_id = create_document_record(filename=filename, minio_path=OBJECT_NAME)

        # Store chunks with embeddings
        chunks_stored = store_chunks_with_embeddings(
            document_id=document_id,
            filename=filename,
            chunks=chunks,
        )
        logger.info(f"✓ Stored {chunks_stored} chunks with embeddings for document_id={document_id}")

    except Exception as e:
        logger.error(f"✗ Failed to store embeddings: {e}")
        import traceback
        traceback.print_exc()
        return

    # Stage 4: Test Retrieval using the retriever module
    logger.info("")
    logger.info("=" * 50)
    logger.info("Stage 4: Testing Retrieval (vector_store ↔ retriever)")
    logger.info("=" * 50)

    try:
        # Use the vector_store's _get_vector_store to verify storage/retrieval compatibility
        vector_store = _get_vector_store()
        
        # Pick a sample query from the first chunk's content (first 50 chars)
        sample_query = chunks[0].page_content[:100] if chunks else "test query"
        logger.info(f"  Testing similarity search with query: '{sample_query[:50]}...'")
        
        # Use PGVector's similarity_search directly
        results = vector_store.similarity_search(sample_query, k=3)
        logger.info(f"✓ Retrieved {len(results)} chunks using vector_store's similarity_search")
        
        retrieved = []
        for i, doc in enumerate(results):
            chunk_id = doc.metadata.get("id", str(i))
            content = doc.page_content
            retrieved.append((chunk_id, content))
            logger.info(f"  [{i+1}] chunk_id={chunk_id}, content_preview='{content[:60]}...'")
        
        # Verify that retrieved chunks have our document's metadata
        if results:
            metadata = results[0].metadata
            logger.info(f"  Metadata from retrieval: {metadata}")
            if metadata.get("document_id") == document_id:
                logger.info(f"✓ Document ID matches! Storage and retrieval are compatible.")
            else:
                logger.warning(f"⚠ Document ID mismatch: expected {document_id}, got {metadata.get('document_id')}")

    except Exception as e:
        logger.error(f"✗ Failed to test retrieval: {e}")
        import traceback
        traceback.print_exc()
        return

    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info("Summary")
    logger.info("=" * 50)
    logger.info(f"  PDF: {OBJECT_NAME}")
    logger.info(f"  Pages extracted: {len(documents)}")
    logger.info(f"  Chunks created: {len(chunks)}")
    logger.info(f"  Chunks stored: {chunks_stored}")
    logger.info(f"  Chunks retrieved: {len(retrieved)}")
    logger.info(f"  Document ID: {document_id}")
    logger.info(f"  Avg chunk size: {avg_size:.0f} characters")
    logger.info("")
    logger.info("Dump files created:")
    logger.info(f"  - {DOCUMENTS_DUMP}")
    logger.info(f"  - {CHUNKS_DUMP}")
    logger.info(f"  - {METADATA_DUMP}")
    logger.info("")
    logger.info("✓ Pipeline test completed successfully!")


if __name__ == "__main__":
    main()
