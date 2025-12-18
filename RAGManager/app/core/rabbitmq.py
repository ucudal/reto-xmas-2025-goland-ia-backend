import json
import logging
from typing import Callable, Optional

import pika
from pika.exceptions import AMQPConnectionError

from app.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQConnection:
    """Handles connection and operations with RabbitMQ"""

    def __init__(self):
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None

    def connect(self):
        """Establishes connection with RabbitMQ"""
        try:
            url = settings.rabbitmq_url
            logger.info(f"Connecting to RabbitMQ at {settings.rabbitmq_host}:{settings.rabbitmq_port}")
            logger.debug(
                f"RabbitMQ URL: amqp://{settings.rabbitmq_user}:***@{settings.rabbitmq_host}:{settings.rabbitmq_port}/"
            )

            self.connection = pika.BlockingConnection(pika.URLParameters(url))
            self.channel = self.connection.channel()
            logger.info("Connected to RabbitMQ")
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            logger.error(f"Configured host: {settings.rabbitmq_host}")
            logger.error(f"Configured port: {settings.rabbitmq_port}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to RabbitMQ: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            raise

    def close(self):
        """Closes the connection"""
        if self.channel and not self.channel.is_closed:
            self.channel.close()
            logger.info("RabbitMQ channel closed")
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ connection closed")

    def declare_queue(self, queue_name: str, durable: bool = True):
        """Declares a queue"""
        if not self.channel:
            self.connect()
        self.channel.queue_declare(queue=queue_name, durable=durable)
        logger.info(f"Queue '{queue_name}' declared")

    def consume_messages(self, queue_name: str, callback: Callable):
        """
        Start consuming messages from the queue.
        
        Args:
            queue_name: Name of the queue to consume from
            callback: Callback function to process messages
        """
        if not self.channel:
            self.connect()

        # Declare queue (idempotent operation)
        self.declare_queue(queue_name)

        # Set QoS to process one message at a time
        self.channel.basic_qos(prefetch_count=1)

        # Start consuming
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=False,  # Manual acknowledgment
        )

        logger.info(f"Started consuming messages from queue '{queue_name}'")
        logger.info("Waiting for messages. To exit press CTRL+C")

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Error while consuming messages: {e}")
            raise
        finally:
            self.close()


# Global instance
rabbitmq = RabbitMQConnection()

