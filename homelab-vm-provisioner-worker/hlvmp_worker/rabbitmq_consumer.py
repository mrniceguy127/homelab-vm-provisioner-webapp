"""RabbitMQ consumer for worker job consumption.

Consumes job messages from RabbitMQ queue and processes them.
Connection details built from component environment variables.
"""

import json
import logging
import os
from typing import Callable, Optional

import pika

logger = logging.getLogger(__name__)


class RabbitMqConsumer:
    """RabbitMQ consumer for job messages."""

    def __init__(
        self,
        host: str,
        port: int,
        vhost: str,
        user: str,
        password: str,
        queue: str,
        exchange: Optional[str] = None,
        routing_key: Optional[str] = None,
    ):
        """Initialize RabbitMQ consumer.

        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            vhost: RabbitMQ vhost
            user: Consumer username
            password: Consumer password
            queue: Queue name to consume from
            exchange: Exchange name (optional, for verification)
            routing_key: Routing key (optional, for verification)
        """
        self.host = host
        self.port = port
        self.vhost = vhost
        self.user = user
        self.password = password
        self.queue = queue
        self.exchange = exchange
        self.routing_key = routing_key
        self.connection = None
        self.channel = None
        self._consumer_tag = None

    def connect(self):
        """Connect to RabbitMQ."""
        credentials = pika.PlainCredentials(self.user, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.vhost,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )

        logger.info(f"Connecting to RabbitMQ at {self.host}:{self.port}/{self.vhost}")
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        # Verify queue exists
        self.channel.queue_declare(queue=self.queue, passive=True, durable=True)

        logger.info(f"Connected to RabbitMQ, consuming from queue: {self.queue}")

    def consume(self, callback: Callable[[dict], bool], prefetch_count: int = 1):
        """Start consuming messages from queue.

        Args:
            callback: Callback function that processes job message.
                      Should return True to ACK, False to NACK.
                      Receives parsed JSON message as dict.
            prefetch_count: Number of messages to prefetch (default: 1)
        """
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")

        # Set QoS prefetch
        self.channel.basic_qos(prefetch_count=prefetch_count)

        def on_message(channel, method, _properties, body):
            """Handle received message."""
            try:
                # Parse message
                message = json.loads(body.decode("utf-8"))
                job_id = message.get('job_id')
                logger.info("")
                logger.info("=" * 70)
                logger.info(f"📬 NEW JOB MESSAGE RECEIVED from RabbitMQ")
                logger.info(f"   Job ID: {job_id}")
                logger.info(f"   Queue: {self.queue}")
                logger.info("=" * 70)

                # Call callback to process
                should_ack = callback(message)

                if should_ack:
                    # ACK message
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info(f"✓ Message ACKed: {job_id}")
                    logger.info("")
                    logger.info("⏳ Waiting for next job message...")
                    logger.info("")
                else:
                    # NACK without requeue (callback decided not to process)
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    logger.warning(f"✗ Message NACKed (no requeue): {job_id}")
                    logger.info("")
                    logger.info("⏳ Waiting for next job message...")
                    logger.info("")

            except json.JSONDecodeError as e:
                logger.error("=" * 70)
                logger.error(f"❌ INVALID MESSAGE: Failed to parse JSON")
                logger.error(f"   Error: {e}")
                logger.error(f"   Raw body: {body[:200]}")  # First 200 chars
                logger.error(f"   → Message rejected (malformed JSON)")
                logger.error("=" * 70)
                # NACK invalid message without requeue
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as e:
                logger.error("=" * 70)
                logger.error(f"❌ ERROR: Exception while processing message")
                logger.error(f"   Error: {e}")
                logger.error(f"   → Message will be requeued for retry")
                logger.error("=" * 70)
                logger.error(f"Full error:", exc_info=True)
                # NACK with requeue for processing errors (transient failure)
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        # Start consuming
        self._consumer_tag = self.channel.basic_consume(
            queue=self.queue, on_message_callback=on_message, auto_ack=False
        )

        logger.info(f"Starting to consume from queue: {self.queue}")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
            self.stop_consuming()

    def stop_consuming(self):
        """Stop consuming messages."""
        if self.channel and self._consumer_tag:
            logger.info("Stopping consumer")
            self.channel.stop_consuming()

    def close(self):
        """Close connection to RabbitMQ."""
        if self.channel:
            self.channel.close()
            self.channel = None
        if self.connection:
            self.connection.close()
            self.connection = None
        logger.info("Closed RabbitMQ connection")

    @classmethod
    def from_env(cls) -> "RabbitMqConsumer":
        """Create consumer from environment variables.

        Required env vars:
            WORKER_QUEUE_HOST
            WORKER_QUEUE_PORT
            WORKER_QUEUE_VHOST
            WORKER_QUEUE_USER
            WORKER_QUEUE_PASSWORD
            WORKER_QUEUE_NAME

        Optional env vars:
            WORKER_QUEUE_EXCHANGE
            WORKER_QUEUE_ROUTING_KEY

        Returns:
            RabbitMqConsumer instance

        Raises:
            ValueError: If required env vars are missing
        """
        required = {
            "host": os.environ.get("WORKER_QUEUE_HOST"),
            "port": os.environ.get("WORKER_QUEUE_PORT"),
            "vhost": os.environ.get("WORKER_QUEUE_VHOST"),
            "user": os.environ.get("WORKER_QUEUE_USER"),
            "password": os.environ.get("WORKER_QUEUE_PASSWORD"),
            "queue": os.environ.get("WORKER_QUEUE_NAME"),
        }

        missing = [key.upper() for key, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return cls(
            host=required["host"],
            port=int(required["port"]),
            vhost=required["vhost"],
            user=required["user"],
            password=required["password"],
            queue=required["queue"],
            exchange=os.environ.get("WORKER_QUEUE_EXCHANGE"),
            routing_key=os.environ.get("WORKER_QUEUE_ROUTING_KEY"),
        )
