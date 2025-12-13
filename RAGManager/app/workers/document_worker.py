import json
import logging
import pika
import socket
import sys
from datetime import datetime
from pika.exceptions import AMQPConnectionError
from app.core.config import settings
from app.core.database_connection import SessionLocal
from app.services.pipeline import process_pdf_pipeline
from app.models.document import Document as DocumentModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_document(document_id: int, minio_path: str, filename: str):
    """
    Processes a complete document using the pipeline:
    1. Downloads PDF from MinIO
    2. Extracts text
    3. Divides into chunks
    4. Generates embeddings
    5. Saves chunks to PostgreSQL

    Args:
        document_id: ID of the document in the database
        minio_path: Path to the file in MinIO
        filename: Original filename
    """
    try:
        logger.info(f"Processing document {document_id}: {filename}")

        # Use the pipeline to process the document
        # The pipeline will handle all steps and save to database
        process_pdf_pipeline(minio_path=minio_path, filename=filename, document_id=document_id)

        logger.info(f"Document {document_id} processed successfully")
        return True

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        logger.exception("Full traceback:")
        raise


def callback(ch, method, properties, body):
    """Callback that executes when a message arrives from RabbitMQ"""
    try:
        # Parse message
        message = json.loads(body)
        document_id = message.get("document_id")
        minio_path = message.get("minio_path")
        filename = message.get("filename")

        if not all([document_id, minio_path, filename]):
            logger.error(f"Invalid message format: {message}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        logger.info(f"Received message for document {document_id}")

        # Process document
        process_document(document_id, minio_path, filename)

        # ACK the message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"Document {document_id} processed and acknowledged")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        logger.exception("Full traceback:")
        # NACK and do not requeue (to avoid infinite loops)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def check_rabbitmq_available(host: str, port: int, timeout: int = 5) -> bool:
    """Check if RabbitMQ is available before attempting connection"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking RabbitMQ availability: {e}")
        return False


def start_worker():
    """Starts the worker that consumes messages from RabbitMQ"""
    connection = None
    channel = None

    try:
        # Check if RabbitMQ is available before connecting
        logger.info(
            f"Checking RabbitMQ availability at {settings.rabbitmq_host}:{settings.rabbitmq_port}"
        )
        if not check_rabbitmq_available(settings.rabbitmq_host, settings.rabbitmq_port):
            logger.error(
                f"RabbitMQ is not available at {settings.rabbitmq_host}:{settings.rabbitmq_port}"
            )
            logger.error("Please ensure RabbitMQ is running: docker-compose up -d")
            sys.exit(1)

        logger.info("RabbitMQ is available, attempting connection...")

        # Configure connection parameters with timeout
        connection_params = pika.URLParameters(settings.rabbitmq_url)
        connection_params.socket_timeout = 10  # 10 seconds timeout
        connection_params.blocked_connection_timeout = 300  # 5 minutes

        # Connect to RabbitMQ
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()

        logger.info("Successfully connected to RabbitMQ")

        # Declare queue
        channel.queue_declare(queue=settings.queue_name, durable=True)
        logger.info(f"Queue '{settings.queue_name}' declared")

        # Configure QoS (process one message at a time)
        channel.basic_qos(prefetch_count=1)

        # Configure consumer
        channel.basic_consume(queue=settings.queue_name, on_message_callback=callback)

        logger.info(
            f"Worker started. Waiting for messages in queue '{settings.queue_name}'. To exit press CTRL+C"
        )
        channel.start_consuming()

    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        if channel:
            try:
                channel.stop_consuming()
            except Exception:
                pass
    except AMQPConnectionError as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        logger.error(f"Host: {settings.rabbitmq_host}, Port: {settings.rabbitmq_port}")
        logger.error("Please check:")
        logger.error("1. RabbitMQ is running: docker-compose ps")
        logger.error("2. RabbitMQ credentials in .env are correct")
        sys.exit(1)
    except socket.timeout:
        logger.error("Connection to RabbitMQ timed out")
        logger.error("Please check if RabbitMQ is running and accessible")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error in worker: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)
    finally:
        if connection and not connection.is_closed:
            try:
                connection.close()
                logger.info("Worker connection closed")
            except Exception:
                pass


if __name__ == "__main__":
    start_worker()

