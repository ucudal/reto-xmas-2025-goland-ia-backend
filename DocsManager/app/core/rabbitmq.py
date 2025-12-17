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

    def declare_exchange(self, exchange_name: str, exchange_type: str = "direct", durable: bool = True):
        """Declares an exchange"""
        if not self.channel:
            self.connect()
        self.channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=exchange_type,
            durable=durable
        )
        logger.info(f"Exchange '{exchange_name}' declared")

    def declare_queue(self, queue_name: str, exchange_name: str = None, durable: bool = True):
        """Declares a queue and optionally binds it to an exchange"""
        if not self.channel:
            self.connect()
        self.channel.queue_declare(queue=queue_name, durable=durable)
        logger.info(f"Queue '{queue_name}' declared")
        
        # Bind to exchange if provided
        if exchange_name:
            self.channel.queue_bind(
                queue=queue_name,
                exchange=exchange_name,
                routing_key=queue_name
            )
            logger.info(f"Queue '{queue_name}' bound to exchange '{exchange_name}'")

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



