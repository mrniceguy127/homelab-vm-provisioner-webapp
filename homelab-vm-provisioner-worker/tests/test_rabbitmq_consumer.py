"""Tests for RabbitMQ consumer."""

import json
import os
import unittest
from unittest.mock import Mock, patch

from hlvmp_worker.rabbitmq_consumer import RabbitMqConsumer


class TestRabbitMqConsumer(unittest.TestCase):
    """Test RabbitMQ consumer."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "host": "localhost",
            "port": 3334,
            "vhost": "provisioner",
            "user": "worker_user",
            "password": "worker_pass",
            "queue": "provisioner.worker.local",
            "exchange": "provisioner.jobs",
            "routing_key": "host.local",
        }

    @patch("hlvmp_worker.rabbitmq_consumer.pika")
    def test_connect(self, mock_pika):
        """Test connection to RabbitMQ."""
        mock_connection = Mock()
        mock_channel = Mock()
        mock_connection.channel.return_value = mock_channel
        mock_pika.BlockingConnection.return_value = mock_connection

        consumer = RabbitMqConsumer(**self.config)
        consumer.connect()

        # Verify connection was created
        self.assertIsNotNone(mock_pika.ConnectionParameters.call_args)

        # Verify connection established
        mock_pika.BlockingConnection.assert_called_once()
        mock_connection.channel.assert_called_once()

        # Verify queue declaration
        mock_channel.queue_declare.assert_called_once_with(
            queue="provisioner.worker.local", passive=True, durable=True
        )

    @patch("hlvmp_worker.rabbitmq_consumer.pika")
    def test_consume_acks_on_success(self, mock_pika):
        """Test message consumption with ACK on successful processing."""
        mock_connection = Mock()
        mock_channel = Mock()
        mock_connection.channel.return_value = mock_channel
        mock_pika.BlockingConnection.return_value = mock_connection

        consumer = RabbitMqConsumer(**self.config)
        consumer.connect()

        # Callback that returns True (should ACK)
        callback = Mock(return_value=True)

        # Set up consume to call callback once then stop
        def fake_consume():
            message = json.dumps(
                {"job_id": "123", "job_type": "provision_vm", "target_host_id": "local"}
            ).encode("utf-8")

            method = Mock()
            method.delivery_tag = "tag-123"
            properties = Mock()

            # Get the on_message_callback that was registered via basic_consume
            on_message_callback = mock_channel.basic_consume.call_args[1]["on_message_callback"]
            on_message_callback(mock_channel, method, properties, message)
            raise KeyboardInterrupt  # Stop after one message

        mock_channel.basic_consume.return_value = "consumer-tag"
        mock_channel.start_consuming.side_effect = fake_consume

        consumer.consume(callback)

        # Verify callback was called with parsed message
        callback.assert_called_once_with(
            {"job_id": "123", "job_type": "provision_vm", "target_host_id": "local"}
        )

        # Verify ACK was sent
        mock_channel.basic_ack.assert_called_once_with(delivery_tag="tag-123")
        mock_channel.basic_nack.assert_not_called()

    @patch("hlvmp_worker.rabbitmq_consumer.pika")
    def test_consume_nacks_on_false_return(self, mock_pika):
        """Test message consumption with NACK when callback returns False."""
        mock_connection = Mock()
        mock_channel = Mock()
        mock_connection.channel.return_value = mock_channel
        mock_pika.BlockingConnection.return_value = mock_connection

        consumer = RabbitMqConsumer(**self.config)
        consumer.connect()

        # Callback that returns False (should NACK without requeue)
        callback = Mock(return_value=False)

        def fake_consume():
            message = json.dumps({"job_id": "456", "job_type": "test", "target_host_id": "remote"}).encode(
                "utf-8"
            )

            method = Mock()
            method.delivery_tag = "tag-456"
            properties = Mock()

            # Get the on_message_callback that was registered via basic_consume
            on_message_callback = mock_channel.basic_consume.call_args[1]["on_message_callback"]
            on_message_callback(mock_channel, method, properties, message)
            raise KeyboardInterrupt

        mock_channel.basic_consume.return_value = "consumer-tag"
        mock_channel.start_consuming.side_effect = fake_consume

        consumer.consume(callback)

        # Verify NACK without requeue
        mock_channel.basic_nack.assert_called_once_with(delivery_tag="tag-456", requeue=False)
        mock_channel.basic_ack.assert_not_called()

    @patch("hlvmp_worker.rabbitmq_consumer.pika")
    def test_consume_nacks_on_json_error(self, mock_pika):
        """Test message consumption with NACK on JSON parse error."""
        mock_connection = Mock()
        mock_channel = Mock()
        mock_connection.channel.return_value = mock_channel
        mock_pika.BlockingConnection.return_value = mock_connection

        consumer = RabbitMqConsumer(**self.config)
        consumer.connect()

        callback = Mock()

        def fake_consume():
            # Invalid JSON
            message = b"not valid json"

            method = Mock()
            method.delivery_tag = "tag-789"
            properties = Mock()

            # Get the on_message_callback that was registered via basic_consume
            on_message_callback = mock_channel.basic_consume.call_args[1]["on_message_callback"]
            on_message_callback(mock_channel, method, properties, message)
            raise KeyboardInterrupt

        mock_channel.basic_consume.return_value = "consumer-tag"
        mock_channel.start_consuming.side_effect = fake_consume

        consumer.consume(callback)

        # Verify callback was not called
        callback.assert_not_called()

        # Verify NACK without requeue (invalid message)
        mock_channel.basic_nack.assert_called_once_with(delivery_tag="tag-789", requeue=False)

    @patch("hlvmp_worker.rabbitmq_consumer.pika")
    def test_consume_nacks_with_requeue_on_processing_error(self, mock_pika):
        """Test message consumption with NACK and requeue on processing exception."""
        mock_connection = Mock()
        mock_channel = Mock()
        mock_connection.channel.return_value = mock_channel
        mock_pika.BlockingConnection.return_value = mock_connection

        consumer = RabbitMqConsumer(**self.config)
        consumer.connect()

        # Callback that raises exception (transient failure)
        callback = Mock(side_effect=RuntimeError("Processing failed"))

        def fake_consume():
            message = json.dumps({"job_id": "999", "job_type": "test", "target_host_id": "local"}).encode(
                "utf-8"
            )

            method = Mock()
            method.delivery_tag = "tag-999"
            properties = Mock()

            # Get the on_message_callback that was registered via basic_consume
            on_message_callback = mock_channel.basic_consume.call_args[1]["on_message_callback"]
            on_message_callback(mock_channel, method, properties, message)
            raise KeyboardInterrupt

        mock_channel.basic_consume.return_value = "consumer-tag"
        mock_channel.start_consuming.side_effect = fake_consume

        consumer.consume(callback)

        # Verify NACK with requeue (transient failure)
        mock_channel.basic_nack.assert_called_once_with(delivery_tag="tag-999", requeue=True)

    @patch("hlvmp_worker.rabbitmq_consumer.pika")
    def test_close(self, mock_pika):
        """Test closing connection."""
        mock_connection = Mock()
        mock_channel = Mock()
        mock_connection.channel.return_value = mock_channel
        mock_pika.BlockingConnection.return_value = mock_connection

        consumer = RabbitMqConsumer(**self.config)
        consumer.connect()
        consumer.close()

        mock_channel.close.assert_called_once()
        mock_connection.close.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "QUEUE_HOST": "rabbitmq.local",
            "QUEUE_PORT": "5672",
            "QUEUE_VHOST": "test",
            "QUEUE_USER": "test_user",
            "QUEUE_PASSWORD": "test_pass",
            "QUEUE_NAME": "test.queue",
            "QUEUE_EXCHANGE": "test.exchange",
            "QUEUE_ROUTING_KEY": "test.key",
        },
    )
    def test_from_env(self):
        """Test creating consumer from environment variables."""
        consumer = RabbitMqConsumer.from_env()

        self.assertEqual(consumer.host, "rabbitmq.local")
        self.assertEqual(consumer.port, 5672)
        self.assertEqual(consumer.vhost, "test")
        self.assertEqual(consumer.user, "test_user")
        self.assertEqual(consumer.password, "test_pass")
        self.assertEqual(consumer.queue, "test.queue")
        self.assertEqual(consumer.exchange, "test.exchange")
        self.assertEqual(consumer.routing_key, "test.key")

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_missing_required(self):
        """Test from_env raises error when required variables missing."""
        with self.assertRaises(ValueError) as context:
            RabbitMqConsumer.from_env()

        self.assertIn("Missing required environment variables", str(context.exception))

    @patch.dict(
        os.environ,
        {
            "QUEUE_HOST": "localhost",
            "QUEUE_PORT": "3334",
            "QUEUE_VHOST": "provisioner",
            "QUEUE_USER": "user",
            # PASSWORD missing
            "QUEUE_NAME": "queue",
        },
    )
    def test_from_env_missing_password(self):
        """Test from_env raises error when password is missing."""
        with self.assertRaises(ValueError) as context:
            RabbitMqConsumer.from_env()

        self.assertIn("PASSWORD", str(context.exception))


if __name__ == "__main__":
    unittest.main()
