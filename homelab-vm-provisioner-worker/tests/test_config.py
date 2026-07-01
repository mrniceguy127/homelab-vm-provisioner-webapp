"""Tests for worker configuration."""

import os
import unittest
from unittest.mock import patch

from hlvmp_worker.config import WorkerConfig


class TestWorkerConfig(unittest.TestCase):
    """Test worker configuration."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch("hlvmp_worker.config.Path.exists", return_value=True):
            config = WorkerConfig(
                database_url="postgresql://localhost/test",
                host_id="test-host",
                api_host="http://localhost",
                api_port=3001,
                provisioner_cli_path="/usr/bin/vmctl",
            )

        self.assertEqual(config.database_url, "postgresql://localhost/test")
        self.assertEqual(config.host_id, "test-host")
        self.assertEqual(config.api_host, "http://localhost")
        self.assertEqual(config.api_port, 3001)
        self.assertEqual(config.api_url, "http://localhost:3001")
        self.assertIsNotNone(config.worker_id)
        self.assertEqual(config.concurrency, 1)
        self.assertIn("/usr/bin", config.provisioner_cli_path)

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        with patch("hlvmp_worker.config.Path.exists", return_value=True):
            config = WorkerConfig(
                database_url="postgresql://localhost/test",
                host_id="test-host",
                api_host="http://localhost",
                api_port=3001,
                worker_id="custom-worker",
                concurrency=3,
                provisioner_cli_path="/custom/path",
            )

        self.assertEqual(config.worker_id, "custom-worker")
        self.assertEqual(config.concurrency, 3)
        self.assertIn("custom", config.provisioner_cli_path)

    def test_concurrency_minimum(self):
        """Test that concurrency is clamped to minimum of 1."""
        with patch("hlvmp_worker.config.Path.exists", return_value=True):
            config = WorkerConfig(
                database_url="postgresql://localhost/test",
                host_id="test-host",
                api_host="http://localhost",
                api_port=3001,
                concurrency=0,
                provisioner_cli_path="/usr/bin/vmctl",
            )

        self.assertEqual(config.concurrency, 1)

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://localhost/test",
            "HOST_ID": "env-host",
            "API_HOST": "http://localhost",
            "API_PORT": "3001",
            "QUEUE_HOST": "localhost",
            "WORKER_ID": "env-worker",
            "PROVISIONER_CONCURRENCY": "2",
            "PROVISIONER_CLI_PATH": "/usr/bin/vmctl",
        },
    )
    @patch("hlvmp_worker.config.Path.exists", return_value=True)
    def test_from_env(self, mock_exists):
        """Test loading configuration from environment variables."""
        config = WorkerConfig.from_env()

        self.assertEqual(config.database_url, "postgresql://localhost/test")
        self.assertEqual(config.host_id, "env-host")
        self.assertEqual(config.api_host, "http://localhost")
        self.assertEqual(config.api_port, 3001)
        self.assertEqual(config.api_url, "http://localhost:3001")
        self.assertEqual(config.worker_id, "env-worker")
        self.assertEqual(config.concurrency, 2)

    @patch.dict(
        os.environ,
        {
            "DB_SERVICE_HOST": "localhost",
            "DB_SERVICE_PORT": "3002",
            "DB_SERVICE_PASSWORD": "secret",
            "HOST_ID": "env-host",
            "API_HOST": "http://localhost",
            "API_PORT": "3001",
            "QUEUE_HOST": "localhost",
            "PROVISIONER_CLI_PATH": "/usr/bin/vmctl",
        },
    )
    @patch("hlvmp_worker.config.Path.exists", return_value=True)
    def test_from_env_with_db_service(self, mock_exists):
        """Test loading DB service base URL from host and port components."""
        config = WorkerConfig.from_env()

        self.assertEqual(config.db_service_base_url, "http://localhost:3002")
        self.assertEqual(config.db_service_password, "secret")
        self.assertEqual(config.host_id, "env-host")

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_missing_host_id(self):
        """Test that from_env raises ValueError when HOST_ID is missing."""
        with self.assertRaises(ValueError) as context:
            WorkerConfig.from_env()

        self.assertIn("HOST_ID", str(context.exception))

    @patch.dict(os.environ, {"HOST_ID": "test-host"}, clear=True)
    def test_from_env_defaults_db_service_base_url(self):
        """Test that DB service base URL defaults so validation proceeds to API_HOST.

        The base URL is auto-constructed from DB_SERVICE_HOST/DB_SERVICE_PORT
        (defaulting to localhost:3002), so a missing DB config never raises.
        With only HOST_ID set, the next required variable (API_HOST) triggers.
        """
        with self.assertRaises(ValueError) as context:
            WorkerConfig.from_env()

        self.assertIn("API_HOST", str(context.exception))

    @patch.dict(
        os.environ,
        {
            "HOST_ID": "test-host",
        },
        clear=True,
    )
    def test_from_env_missing_api_host(self):
        """Test that from_env raises ValueError when API_HOST is missing."""
        with self.assertRaises(ValueError) as context:
            WorkerConfig.from_env()

        self.assertIn("API_HOST", str(context.exception))

    @patch.dict(
        os.environ,
        {
            "HOST_ID": "test-host",
            "API_HOST": "http://localhost",
        },
        clear=True,
    )
    def test_from_env_missing_api_port(self):
        """Test that from_env raises ValueError when API_PORT is missing."""
        with self.assertRaises(ValueError) as context:
            WorkerConfig.from_env()

        self.assertIn("API_PORT", str(context.exception))

    @patch.dict(
        os.environ,
        {
            "HOST_ID": "test-host",
            "API_HOST": "http://localhost",
            "API_PORT": "not-a-number",
            "QUEUE_HOST": "localhost",
            "PROVISIONER_CLI_PATH": "/usr/bin/vmctl",
        },
        clear=True,
    )
    @patch("hlvmp_worker.config.Path.exists", return_value=True)
    def test_from_env_invalid_api_port(self, mock_exists):
        """Test that from_env raises ValueError when API_PORT is not a valid integer."""
        with self.assertRaises(ValueError) as context:
            WorkerConfig.from_env()

        self.assertIn("API_PORT must be a valid integer", str(context.exception))

    @patch.dict(
        os.environ,
        {
            "HOST_ID": "test-host",
            "API_HOST": "http://localhost",
            "API_PORT": "3001",
        },
        clear=True,
    )
    def test_from_env_missing_queue_host(self):
        """Test that from_env raises ValueError when QUEUE_HOST is missing."""
        with self.assertRaises(ValueError) as context:
            WorkerConfig.from_env()

        self.assertIn("QUEUE_HOST", str(context.exception))

    def test_init_with_explicit_provisioner_path(self):
        """Test initialization with explicit provisioner CLI path."""
        with patch("hlvmp_worker.config.Path.exists", return_value=True):
            config = WorkerConfig(
                database_url="postgresql://localhost/test",
                host_id="test-host",
                api_host="http://localhost",
                api_port=3001,
                worker_id="test-worker",
                provisioner_cli_path="/test/path",
            )

        repr_str = repr(config)

        self.assertIn("test-host", repr_str)
        self.assertIn("test-worker", repr_str)
        self.assertIn("concurrency=1", repr_str)
        self.assertIn("api_host", repr_str)
        self.assertIn("api_port", repr_str)
        self.assertIn("provisioner_cli_path", repr_str)

    def test_dry_run_default_false(self):
        """Test that dry_run defaults to False."""
        with patch("hlvmp_worker.config.Path.exists", return_value=True):
            config = WorkerConfig(
                database_url="postgresql://localhost/test",
                host_id="test-host",
                api_host="http://localhost",
                api_port=3001,
                provisioner_cli_path="/usr/bin/vmctl",
            )

        self.assertFalse(config.dry_run)

    def test_dry_run_explicit_true(self):
        """Test that dry_run can be explicitly enabled."""
        with patch("hlvmp_worker.config.Path.exists", return_value=True):
            config = WorkerConfig(
                database_url="postgresql://localhost/test",
                host_id="test-host",
                api_host="http://localhost",
                api_port=3001,
                provisioner_cli_path="/usr/bin/vmctl",
                dry_run=True,
            )

        self.assertTrue(config.dry_run)

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://localhost/test",
            "HOST_ID": "env-host",
            "API_HOST": "http://localhost",
            "API_PORT": "3001",
            "QUEUE_HOST": "localhost",
            "PROVISIONER_CLI_PATH": "/usr/bin/vmctl",
            "WORKER_DRY_RUN": "true",
        },
    )
    @patch("hlvmp_worker.config.Path.exists", return_value=True)
    def test_from_env_dry_run_true(self, mock_exists):
        """Test loading dry_run=true from environment."""
        config = WorkerConfig.from_env()

        self.assertTrue(config.dry_run)

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://localhost/test",
            "HOST_ID": "env-host",
            "API_HOST": "http://localhost",
            "API_PORT": "3001",
            "QUEUE_HOST": "localhost",
            "PROVISIONER_CLI_PATH": "/usr/bin/vmctl",
            "WORKER_DRY_RUN": "1",
        },
    )
    @patch("hlvmp_worker.config.Path.exists", return_value=True)
    def test_from_env_dry_run_1(self, mock_exists):
        """Test loading dry_run=1 from environment."""
        config = WorkerConfig.from_env()

        self.assertTrue(config.dry_run)

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://localhost/test",
            "HOST_ID": "env-host",
            "API_HOST": "http://localhost",
            "API_PORT": "3001",
            "QUEUE_HOST": "localhost",
            "PROVISIONER_CLI_PATH": "/usr/bin/vmctl",
            "WORKER_DRY_RUN": "false",
        },
    )
    @patch("hlvmp_worker.config.Path.exists", return_value=True)
    def test_from_env_dry_run_false(self, mock_exists):
        """Test loading dry_run=false from environment."""
        config = WorkerConfig.from_env()

        self.assertFalse(config.dry_run)

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://localhost/test",
            "HOST_ID": "env-host",
            "API_HOST": "http://localhost",
            "API_PORT": "3001",
            "QUEUE_HOST": "localhost",
            "PROVISIONER_CLI_PATH": "/usr/bin/vmctl",
        },
    )
    @patch("hlvmp_worker.config.Path.exists", return_value=True)
    def test_from_env_dry_run_default(self, mock_exists):
        """Test that dry_run defaults to False when not in environment."""
        config = WorkerConfig.from_env()

        self.assertFalse(config.dry_run)

    def test_repr_includes_dry_run(self):
        """Test that __repr__ includes dry_run status."""
        with patch("hlvmp_worker.config.Path.exists", return_value=True):
            config = WorkerConfig(
                database_url="postgresql://localhost/test",
                host_id="test-host",
                api_host="http://localhost",
                api_port=3001,
                worker_id="test-worker",
                provisioner_cli_path="/test/path",
                dry_run=True,
            )

        repr_str = repr(config)

        self.assertIn("dry_run=True", repr_str)


if __name__ == "__main__":
    unittest.main()
