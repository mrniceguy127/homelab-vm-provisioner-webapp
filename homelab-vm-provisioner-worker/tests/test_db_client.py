"""Tests for worker database client."""

import json
import unittest
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError, URLError

from hlvmp_worker.db_client import DatabaseClient


class TestDatabaseClient(unittest.TestCase):
    """Test database client for job operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = DatabaseClient("http://localhost:3002", "test-password")

    @patch("hlvmp_worker.db_client.urlopen")
    def test_health_check_success(self, mock_urlopen):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.health_check()

        self.assertTrue(result)

    @patch("hlvmp_worker.db_client.urlopen")
    def test_health_check_failure(self, mock_urlopen):
        """Test health check when service is down."""
        mock_urlopen.side_effect = URLError("Connection refused")

        result = self.client.health_check()

        self.assertFalse(result)

    @patch("hlvmp_worker.db_client.urlopen")
    def test_claim_next_job_success(self, mock_urlopen):
        """Test claiming a job successfully."""
        job_data = {
            "job": {
                "id": 1,
                "type": "provision_vm",
                "status": "queued",
                "targetHostId": "host1",
                "payload": {"configPath": "/path/to/config.yaml"},
            }
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(job_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.claim_next_job("host1", "worker1")

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["type"], "provision_vm")

    @patch("hlvmp_worker.db_client.urlopen")
    def test_claim_next_job_none_available(self, mock_urlopen):
        """Test claiming when no jobs are available."""
        mock_response = Mock()
        mock_response.code = 404
        mock_response.read.return_value = b'{"error": "No jobs available"}'

        mock_urlopen.side_effect = HTTPError(
            "http://test", 404, "Not Found", {}, mock_response
        )

        result = self.client.claim_next_job("host1", "worker1")

        self.assertIsNone(result)

    @patch("hlvmp_worker.db_client.urlopen")
    def test_mark_job_running(self, mock_urlopen):
        """Test marking a job as running."""
        job_data = {
            "job": {
                "id": 1,
                "type": "provision_vm",
                "status": "running",
                "targetHostId": "host1",
            }
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(job_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.mark_job_running(1, "worker1")

        self.assertEqual(result["id"], 1)
        self.assertEqual(result["status"], "running")

    @patch("hlvmp_worker.db_client.urlopen")
    def test_mark_job_succeeded(self, mock_urlopen):
        """Test marking a job as succeeded."""
        job_data = {
            "job": {
                "id": 1,
                "type": "provision_vm",
                "status": "succeeded",
                "result": {"success": True},
            }
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(job_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.mark_job_succeeded(1, {"success": True})

        self.assertEqual(result["id"], 1)
        self.assertEqual(result["status"], "succeeded")

    @patch("hlvmp_worker.db_client.urlopen")
    def test_mark_job_failed(self, mock_urlopen):
        """Test marking a job as failed."""
        job_data = {
            "job": {
                "id": 1,
                "type": "provision_vm",
                "status": "failed",
                "error": "Test error",
            }
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(job_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.mark_job_failed(1, "Test error", retriable=False)

        self.assertEqual(result["id"], 1)
        self.assertEqual(result["status"], "failed")

    @patch("hlvmp_worker.db_client.urlopen")
    def test_append_job_event(self, mock_urlopen):
        """Test appending an event to a job."""
        event_data = {
            "event": {
                "id": 1,
                "jobId": 1,
                "level": "info",
                "message": "Test message",
            }
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(event_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.append_job_event(1, "info", "Test message")

        self.assertEqual(result["jobId"], 1)
        self.assertEqual(result["level"], "info")
        self.assertEqual(result["message"], "Test message")

    @patch("hlvmp_worker.db_client.urlopen")
    def test_acquire_resource_locks_success(self, mock_urlopen):
        """Test acquiring resource locks successfully."""
        lock_data = {"acquired": True}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(lock_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.acquire_resource_locks(1, "worker1", ["vm:test-vm"])

        self.assertTrue(result)

    @patch("hlvmp_worker.db_client.urlopen")
    def test_acquire_resource_locks_conflict(self, mock_urlopen):
        """Test acquiring resource locks when already locked."""
        mock_response = Mock()
        mock_response.code = 409
        mock_response.read.return_value = b'{"error": "Resource locked"}'

        mock_urlopen.side_effect = HTTPError(
            "http://test", 409, "Conflict", {}, mock_response
        )

        result = self.client.acquire_resource_locks(1, "worker1", ["vm:test-vm"])

        self.assertFalse(result)

    @patch("hlvmp_worker.db_client.urlopen")
    def test_release_resource_locks(self, mock_urlopen):
        """Test releasing resource locks."""
        lock_data = {"released": 2}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(lock_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.release_resource_locks(1, "worker1")

        self.assertEqual(result, 2)

    @patch("hlvmp_worker.db_client.urlopen")
    def test_request_with_http_error(self, mock_urlopen):
        """Test request handling when HTTP error occurs."""
        mock_response = Mock()
        mock_response.code = 500
        mock_response.read.return_value = b'{"error": "Internal server error"}'

        mock_urlopen.side_effect = HTTPError(
            "http://test", 500, "Internal Server Error", {}, mock_response
        )

        with self.assertRaises(RuntimeError) as context:
            self.client.mark_job_running(1, "worker1")

        self.assertIn("Status 500", str(context.exception))

    @patch("hlvmp_worker.db_client.urlopen")
    def test_request_with_url_error(self, mock_urlopen):
        """Test request handling when connection fails."""
        mock_urlopen.side_effect = URLError("Connection refused")

        with self.assertRaises(RuntimeError) as context:
            self.client.mark_job_running(1, "worker1")

        self.assertIn("Failed to connect", str(context.exception))


if __name__ == "__main__":
    unittest.main()
