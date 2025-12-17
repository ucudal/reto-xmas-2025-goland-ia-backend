# PDF processing utilities for extracting content from PDFs stored in MinIO.
# Tables are extracted as separate atomic blocks to prevent chunking from splitting them.

import io
import logging
from dataclasses import dataclass
from enum import Enum

import pdfplumber
from langchain_core.documents import Document
from minio import Minio

from app.core.config import settings
from app.services.minio_client import download_object

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Type of content block extracted from PDF."""

    TEXT = "text"
    TABLE = "table"


@dataclass
class ContentBlock:
    """A block of content extracted from a PDF page."""

    content_type: ContentType
    content: str
    y_position: float  # For ordering on page
    context: str = ""  # Text immediately preceding (for tables)


def _sanitize_cell(cell) -> str:
    """Safely convert a cell value to string."""
    if cell is None:
        return ""
    if isinstance(cell, (str, int, float, bool)):
        return str(cell).strip()
    try:
        return str(cell).strip()
    except Exception:
        return ""


def _table_to_markdown(table_data: list[list]) -> str:
    """Convert extracted table to Markdown format."""
    if not table_data or not any(table_data):
        return ""

    # Clean all cells
    cleaned = [
        [_sanitize_cell(cell) for cell in row]
        for row in table_data
        if any(cell is not None for cell in row)
    ]

    if not cleaned:
        return ""

    # Normalize column count
    col_count = max(len(row) for row in cleaned)
    normalized = [row + [""] * (col_count - len(row)) for row in cleaned]

    # Build markdown
    lines = []
    for i, row in enumerate(normalized):
        escaped = [c.replace("|", "\\|") for c in row]
        lines.append("| " + " | ".join(escaped) + " |")
        if i == 0:
            lines.append("| " + " | ".join(["---"] * col_count) + " |")

    return "\n".join(lines)


def _get_context_above(page, y_position: float, max_chars: int = 150) -> str:
    """Get text immediately above a Y position."""
    try:
        search_height = min(80, y_position)
        if search_height <= 0:
            return ""
        region = page.within_bbox(
            (0, max(0, y_position - search_height), page.width, y_position)
        )
        text = region.extract_text()
        if not text:
            return ""
        text = text.strip()
        # Get last lines up to max_chars
        if len(text) > max_chars:
            lines = text.split("\n")
            result = ""
            for line in reversed(lines):
                if len(result) + len(line) + 1 <= max_chars:
                    result = line + ("\n" + result if result else "")
                else:
                    break
            return result.strip() or text[-max_chars:]
        return text
    except Exception:
        return ""


def _extract_content_blocks(page, page_num: int) -> list[ContentBlock]:
    """
    Extract content from a page as ordered blocks (text and tables).
    Tables are kept as atomic units with their preceding context.
    """
    blocks: list[ContentBlock] = []

    tables = page.find_tables()

    if not tables:
        # No tables - single text block
        text = page.extract_text()
        if text and text.strip():
            blocks.append(
                ContentBlock(
                    content_type=ContentType.TEXT,
                    content=text.strip(),
                    y_position=0,
                )
            )
        return blocks

    # Sort tables by vertical position
    table_info = []
    for table in tables:
        try:
            bbox = table.bbox  # (x0, top, x1, bottom)
            table_data = table.extract()
            markdown = _table_to_markdown(table_data)
            if markdown:
                context = _get_context_above(page, bbox[1])
                table_info.append((bbox, context, markdown))
        except Exception as e:
            logger.warning("Failed to process table on page %d: %s", page_num, e)

    table_info.sort(key=lambda x: x[0][1])  # Sort by top Y

    # Extract text regions between tables
    page_height = page.height
    page_width = page.width
    current_y = 0

    for bbox, context, markdown in table_info:
        table_top = bbox[1]
        table_bottom = bbox[3]

        # Text region above this table
        if table_top > current_y + 5:  # 5pt tolerance
            try:
                region = page.within_bbox((0, current_y, page_width, table_top))
                text = region.extract_text()
                if text and text.strip():
                    blocks.append(
                        ContentBlock(
                            content_type=ContentType.TEXT,
                            content=text.strip(),
                            y_position=current_y,
                        )
                    )
            except Exception:
                pass

        # Table block (with context embedded)
        blocks.append(
            ContentBlock(
                content_type=ContentType.TABLE,
                content=markdown,
                y_position=table_top,
                context=context,
            )
        )

        current_y = table_bottom

    # Text after last table
    if current_y < page_height - 5:
        try:
            region = page.within_bbox((0, current_y, page_width, page_height))
            text = region.extract_text()
            if text and text.strip():
                blocks.append(
                    ContentBlock(
                        content_type=ContentType.TEXT,
                        content=text.strip(),
                        y_position=current_y,
                    )
                )
        except Exception:
            pass

    return blocks


def pdf_to_content_blocks(
    object_name: str,
    bucket_name: str | None = None,
    minio_client: Minio | None = None,
) -> list[tuple[ContentBlock, dict]]:
    """
    Extract PDF as a list of content blocks with metadata.

    Returns:
        List of (ContentBlock, metadata) tuples
    """
    if bucket_name is None:
        bucket_name = settings.minio_bucket

    pdf_bytes = download_object(object_name, bucket_name, minio_client)

    results: list[tuple[ContentBlock, dict]] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, start=1):
            try:
                blocks = _extract_content_blocks(page, page_num)

                base_metadata = {
                    "source": f"minio://{bucket_name}/{object_name}",
                    "bucket": bucket_name,
                    "object_name": object_name,
                    "page": page_num,
                    "total_pages": total_pages,
                    "filename": object_name.split("/")[-1],
                }

                for block in blocks:
                    metadata = {
                        **base_metadata,
                        "content_type": block.content_type.value,
                    }
                    results.append((block, metadata))

            except Exception as e:
                logger.error(
                    "Failed to process page %d of %s: %s", page_num, object_name, e
                )

    logger.info("Extracted %d content blocks from %s", len(results), object_name)
    return results


def pdf_to_document(
    object_name: str,
    bucket_name: str | None = None,
    minio_client: Minio | None = None,
) -> list[Document]:
    """
    Load a PDF file from MinIO and return a list of Document objects.
    Tables are extracted as separate Documents with content_type metadata.

    Args:
        object_name: Path/name of the PDF object in the bucket
        bucket_name: Name of the MinIO bucket (defaults to settings.minio_bucket)
        minio_client: Optional MinIO client (creates one if not provided)

    Returns:
        List of Document objects (text blocks and tables as separate documents)
    """
    blocks_with_meta = pdf_to_content_blocks(object_name, bucket_name, minio_client)

    documents = []
    for block, metadata in blocks_with_meta:
        if block.content_type == ContentType.TABLE:
            # Include context with table
            content = block.content
            if block.context:
                content = f"**{block.context}**\n\n{content}"
        else:
            content = block.content

        documents.append(
            Document(
                page_content=content,
                metadata=metadata,
            )
        )

    return documents
