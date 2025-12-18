"""RabbitMQ consumer for processing PDFs from MinIO events."""

import json
import logging
from urllib.parse import unquote

from app.core.config import settings
from app.core.rabbitmq import RabbitMQConnection
from app.services.pipeline import process_pdf_pipeline

logger = logging.getLogger(__name__)


def extract_pdf_path(message_body: dict) -> str:
    """
    Extract the PDF path from MinIO event message.
    
    Args:
        message_body: Parsed JSON message from MinIO
        
    Returns:
        str: Decoded object path (e.g., "rag-docs/file.pdf")
        
    Raises:
        ValueError: If message structure is invalid
    """
    records = message_body.get("Records", [])
    if not records:
        raise ValueError("No Records found in message")
    
    # Extract key from Records[0].s3.object.key
    try:
        object_key = records[0]["s3"]["object"]["key"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Invalid message structure: {e}") from e
    
    # URL decode: rag-docs%2Farchivo.pdf -> rag-docs/archivo.pdf
    decoded_path = unquote(object_key)
    
    return decoded_path


def message_callback(ch, method, properties, body):
    """
    Callback function to process RabbitMQ messages.
    
    Args:
        ch: Channel
        method: Method
        properties: Properties
        body: Message body (bytes)
    """
    try:
        # Parse JSON message
        message = json.loads(body)
        logger.info(f"Received message from RabbitMQ")
        logger.debug(f"Message content: {message}")
        
        # Extract PDF path
        pdf_path = extract_pdf_path(message)
        logger.info(f"Extracted PDF path: {pdf_path}")
        
        # Only process PDFs
        if not pdf_path.lower().endswith('.pdf'):
            logger.info(f"Skipping non-PDF file: {pdf_path}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        # Call the existing pipeline
        logger.info(f"Starting PDF processing pipeline for: {pdf_path}")
        document_id = process_pdf_pipeline(pdf_path)
        logger.info(f"PDF processed successfully: {pdf_path} -> Document ID: {document_id}")
        
        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"Message acknowledged for: {pdf_path}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON message: {e}")
        # NACK without requeue - malformed messages won't be fixed by retrying
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except ValueError as e:
        logger.error(f"Invalid message structure: {e}")
        # NACK without requeue - invalid structure won't be fixed by retrying
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        # NACK without requeue to avoid infinite loops
        # In production, consider implementing a dead-letter queue
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_consumer():
    """
    Start the RabbitMQ consumer to process PDF files.
    
    This function runs in a blocking loop and should be executed
    in a separate thread or process.
    """
    logger.info("Starting PDF processor consumer")
    
    try:
        # Create RabbitMQ connection
        rabbitmq = RabbitMQConnection()
        rabbitmq.connect()
        
        # Start consuming messages
        queue_name = settings.rabbitmq_queue_name
        logger.info(f"Consuming messages from queue: {queue_name}")
        
        rabbitmq.consume_messages(
            queue_name=queue_name,
            callback=message_callback
        )
        
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in consumer: {e}", exc_info=True)
        raise

