from typing import List, Tuple
from openai import OpenAI
import logging
from langchain_core.documents import Document
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service to generate embeddings using OpenAI"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimension

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generates an embedding for a text

        Args:
            text: Text to generate the embedding for

        Returns:
            List of floats representing the embedding vector (1536 dimensions)
        """
        try:
            response = self.client.embeddings.create(
                model=self.model, input=text, dimensions=self.dimensions
            )

            embedding = response.data[0].embedding

            if len(embedding) != self.dimensions:
                raise ValueError(f"Expected {self.dimensions} dimensions, got {len(embedding)}")

            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for multiple texts (more efficient)

        Args:
            texts: List of texts

        Returns:
            List of embeddings
        """
        try:
            # Validate API key
            if not settings.openai_api_key or settings.openai_api_key.strip() == "":
                raise ValueError("OPENAI_API_KEY is not configured")

            logger.info(f"Generating embeddings for {len(texts)} chunks...")
            if texts:
                logger.debug(f"First chunk preview: {texts[0][:100]}...")

            # Add timeout to the call (60 seconds)
            response = self.client.embeddings.create(
                model=self.model, input=texts, dimensions=self.dimensions, timeout=60.0
            )

            embeddings = [item.embedding for item in response.data]

            logger.info(f"Generated {len(embeddings)} embeddings in batch")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            logger.exception("Full traceback:")
            raise


# Global instance
embedding_service = EmbeddingService()


def chunks_to_embeddings(chunks: List[Document]) -> List[Tuple[str, List[float]]]:
    """
    Generates embeddings for each chunk using OpenAI's embedding API.

    Args:
        chunks: List of LangChain Document chunks to embed

    Returns:
        List[Tuple[str, List[float]]]: List of tuples containing (content, embedding_vector)
        where embedding_vector is a list of floats with dimension 1536
    """
    # Extract text content from Document objects
    texts = [chunk.page_content for chunk in chunks]

    # Generate embeddings in batch
    embeddings = embedding_service.generate_embeddings_batch(texts)

    # Return as list of tuples
    return [(text, embedding) for text, embedding in zip(texts, embeddings)]

