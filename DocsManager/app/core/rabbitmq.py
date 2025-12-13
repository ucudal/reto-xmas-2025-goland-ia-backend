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
        """
        Initialize the RabbitMQConnection instance.
        
        Sets up container attributes used to hold the pika connection and channel; both are initialized to None and will be created when connect() is called.
        """
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None

    def connect(self):
        """
        Establishes a BlockingConnection to RabbitMQ and creates a channel on the instance.
        
        Sets self.connection to a pika.BlockingConnection (using settings.rabbitmq_url) and self.channel to the connection's channel. Re-raises connection-related and other unexpected exceptions.
        
        Raises:
            AMQPConnectionError: if the client cannot connect to the RabbitMQ broker.
            Exception: for other unexpected errors during connection setup.
        """
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
        """
        Close the channel and connection to RabbitMQ if they exist and are open.
        """
        if self.channel and not self.channel.is_closed:
            self.channel.close()
            logger.info("RabbitMQ channel closed")
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ connection closed")

    def declare_queue(self, queue_name: str, durable: bool = True):
        """
        Ensure a channel exists and declare the named queue on the RabbitMQ server.
        
        If no channel is present this method establishes a connection and channel, then declares the queue with the given durability so messages are persisted across broker restarts when durable is True.
        
        Parameters:
            queue_name (str): Name of the queue to declare.
            durable (bool): Whether the queue should survive broker restarts (defaults to True).
        """
        if not self.channel:
            self.connect()
        self.channel.queue_declare(queue=queue_name, durable=durable)
        logger.info(f"Queue '{queue_name}' declared")

    def publish_message(self, queue_name: str, message: dict):
        """
        Publish a JSON-serializable dictionary to the specified RabbitMQ queue.
        
        Serializes `message` to JSON, ensures the channel is open and the queue exists, and publishes the message with delivery_mode=2 (persistent).
        
        Parameters:
            queue_name (str): Name of the RabbitMQ queue to publish to.
            message (dict): Message payload that will be serialized to JSON.
        
        Raises:
            Exception: Propagates any error encountered during connection, queue declaration, serialization, or publish.
        """
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
