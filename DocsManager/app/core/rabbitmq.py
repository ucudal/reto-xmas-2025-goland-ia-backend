import pika
from pika.exceptions import AMQPConnectionError
from typing import Optional
import logging
import json
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

    def publish_message(self, queue_name: str, message: dict):
        """Publishes a message to the queue"""
        try:
            if not self.channel:
                self.connect()

            if not self.channel.is_open:
                self.connect()

            # Ensure the queue exists
            self.declare_queue(queue_name)

            message_body = json.dumps(message)

            self.channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Makes the message persistent
                ),
            )
            logger.info(f"Message published to queue '{queue_name}'")
        except Exception as e:
            logger.error(f"Failed to publish message to RabbitMQ: {e}")
            logger.error(f"Host: {settings.rabbitmq_host}, Port: {settings.rabbitmq_port}")
            raise


# Global instance
rabbitmq = RabbitMQConnection()



