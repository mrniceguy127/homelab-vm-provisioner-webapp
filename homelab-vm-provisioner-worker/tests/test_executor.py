"""Tests for worker job executor."""

import unittest
from unittest.mock import Mock, patch

from hlvmp_worker.executor import JobExecutionError, JobExecutor


class TestJobExecutor(unittest.TestCase):
    """Test job executor for provisioner operations."""

    def test_init_raises_when_vmctl_missing(self):
        """Test executor initialization fails without vmctl."""
        with (
            patch("hlvmp_worker.executor.Path.exists", return_value=False),
            self.assertRaises(ValueError) as context,
        ):
            JobExecutor("/fake/path/to/cli")

        self.assertIn("vmctl not found", str(context.exception))

    def setUp(self):
        """Set up test fixtures."""
        with patch("hlvmp_worker.executor.Path.exists", return_value=True):
            self.executor = JobExecutor("/fake/path/to/cli")

    def test_get_supported_job_types(self):
        """Test getting list of supported job types."""
        job_types = self.executor.get_supported_job_types()

        self.assertIn("provision_vm", job_types)
        self.assertIn("destroy_vm", job_types)
        self.assertIn("clone_vm", job_types)
        self.assertIn("start_vm", job_types)
        self.assertIn("stop_vm", job_types)
        self.assertIn("reconcile_vm_networking", job_types)

    def test_get_resource_locks_for_vm_job(self):
        """Test resource lock calculation for VM-specific jobs."""
        job = {
            "type": "provision_vm",
            "targetHostId": "host1",
            "targetVmId": "test-vm",
        }

        locks = self.executor.get_resource_locks(job)

        self.assertEqual(locks, ["vm:test-vm"])

    def test_get_resource_locks_for_vm_job_no_vm_id(self):
        """Test resource lock fallback when VM ID is missing."""
        job = {
            "type": "provision_vm",
            "targetHostId": "host1",
            "targetVmId": None,
        }

        locks = self.executor.get_resource_locks(job)

        self.assertEqual(locks, ["host:host1"])

    def test_get_resource_locks_for_networking_job(self):
        """Test resource lock calculation for networking jobs."""
        job = {
            "type": "reconcile_vm_networking",
            "targetHostId": "host1",
        }

        locks = self.executor.get_resource_locks(job)

        # Should be sorted: firewall before network
        self.assertEqual(locks, ["firewall:host1", "network:host1"])

    def test_get_resource_locks_for_multiple_vms(self):
        """Test that locks are sorted for deterministic ordering."""
        job1 = {
            "type": "start_vm",
            "targetHostId": "host1",
            "targetVmId": "vm-a",
        }
        job2 = {
            "type": "start_vm",
            "targetHostId": "host1",
            "targetVmId": "vm-b",
        }

        locks1 = self.executor.get_resource_locks(job1)
        locks2 = self.executor.get_resource_locks(job2)

        # Each should have exactly one lock
        self.assertEqual(len(locks1), 1)
        self.assertEqual(len(locks2), 1)
        self.assertNotEqual(locks1, locks2)

    def test_get_resource_locks_for_unknown_job_uses_host_lock(self):
        """Test unknown job types fall back to a host-level lock."""
        job = {
            "type": "custom_job",
            "targetHostId": "host1",
        }

        locks = self.executor.get_resource_locks(job)

        self.assertEqual(locks, ["host:host1"])

    @patch("hlvmp_worker.executor.subprocess.run")
    def test_run_vmctl_nonzero_exit_raises_job_execution_error(self, mock_run):
        """Test vmctl failures preserve the command error message."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="boom")

        with self.assertRaises(JobExecutionError) as context:
            self.executor._run_vmctl("start", "test-vm")

        self.assertIn("vmctl command failed: boom", str(context.exception))
        self.assertTrue(context.exception.retriable)

    @patch("hlvmp_worker.executor.subprocess.run", side_effect=FileNotFoundError("missing"))
    def test_run_vmctl_missing_binary_raises_non_retriable_error(self, mock_run):
        """Test missing vmctl binary is reported as non-retriable."""
        with self.assertRaises(JobExecutionError) as context:
            self.executor._run_vmctl("start", "test-vm")

        self.assertIn("vmctl not found", str(context.exception))
        self.assertFalse(context.exception.retriable)

    @patch("hlvmp_worker.executor.subprocess.run", side_effect=OSError("exec failed"))
    def test_run_vmctl_unexpected_error_is_retriable(self, mock_run):
        """Test unexpected vmctl invocation errors are retriable."""
        with self.assertRaises(JobExecutionError) as context:
            self.executor._run_vmctl("start", "test-vm")

        self.assertIn("Failed to execute vmctl", str(context.exception))
        self.assertTrue(context.exception.retriable)

    @patch("hlvmp_worker.executor.subprocess.run")
    @patch("hlvmp_worker.executor.Path.exists", return_value=True)
    def test_execute_provision_vm_success(self, mock_exists, mock_run):
        """Test successful VM provision execution."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        job = {
            "type": "provision_vm",
            "payload": {"configPath": "/tmp/test-config.yaml"},
        }

        result = self.executor.execute_job(job)

        self.assertTrue(result["success"])
        self.assertEqual(result["configPath"], "/tmp/test-config.yaml")
        mock_run.assert_called_once()

    def test_execute_provision_vm_missing_config_path(self):
        """Test provision VM with missing config path."""
        job = {
            "type": "provision_vm",
            "payload": {},
        }

        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job(job)

        self.assertIn("configPath", str(context.exception))
        self.assertFalse(context.exception.retriable)

    def test_execute_provision_vm_config_not_found(self):
        """Test provision VM when config file doesn't exist."""
        job = {
            "type": "provision_vm",
            "payload": {"configPath": "/nonexistent/config.yaml"},
        }

        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job(job)

        self.assertIn("not found", str(context.exception))
        self.assertFalse(context.exception.retriable)

    @patch("hlvmp_worker.executor.subprocess.run")
    def test_execute_destroy_vm_success(self, mock_run):
        """Test successful VM destroy execution."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        job = {
            "type": "destroy_vm",
            "payload": {"vmName": "test-vm"},
        }

        result = self.executor.execute_job(job)

        self.assertTrue(result["success"])
        self.assertEqual(result["vmName"], "test-vm")
        mock_run.assert_called_once()

    def test_execute_destroy_vm_missing_name(self):
        """Test destroy VM with missing name."""
        job = {
            "type": "destroy_vm",
            "payload": {},
        }

        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job(job)

        self.assertIn("vmName", str(context.exception))
        self.assertFalse(context.exception.retriable)

    @patch("hlvmp_worker.executor.subprocess.run")
    @patch("hlvmp_worker.executor.Path.exists", return_value=True)
    def test_execute_clone_vm_success(self, mock_exists, mock_run):
        """Test successful VM clone execution."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        job = {
            "type": "clone_vm",
            "payload": {
                "sourceVmName": "source-vm",
                "configPath": "/tmp/target-config.yaml",
            },
        }

        result = self.executor.execute_job(job)

        self.assertTrue(result["success"])
        self.assertEqual(result["sourceVmName"], "source-vm")
        mock_run.assert_called_once()

    def test_execute_clone_vm_missing_source_name(self):
        """Test clone VM requires a source VM name."""
        job = {
            "type": "clone_vm",
            "payload": {"configPath": "/tmp/target-config.yaml"},
        }

        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job(job)

        self.assertIn("sourceVmName", str(context.exception))
        self.assertFalse(context.exception.retriable)

    def test_execute_clone_vm_missing_config_path(self):
        """Test clone VM requires a target config path."""
        job = {
            "type": "clone_vm",
            "payload": {"sourceVmName": "source-vm"},
        }

        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job(job)

        self.assertIn("configPath", str(context.exception))
        self.assertFalse(context.exception.retriable)

    def test_execute_clone_vm_config_not_found(self):
        """Test clone VM validates the target config path exists."""
        job = {
            "type": "clone_vm",
            "payload": {
                "sourceVmName": "source-vm",
                "configPath": "/nonexistent/config.yaml",
            },
        }

        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job(job)

        self.assertIn("Config file not found", str(context.exception))
        self.assertFalse(context.exception.retriable)

    @patch("hlvmp_worker.executor.subprocess.run")
    def test_execute_start_vm_success(self, mock_run):
        """Test successful VM start execution."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        job = {
            "type": "start_vm",
            "payload": {"vmName": "test-vm"},
        }

        result = self.executor.execute_job(job)

        self.assertTrue(result["success"])
        mock_run.assert_called_once()

    def test_execute_start_vm_missing_name(self):
        """Test start VM requires a VM name."""
        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job({"type": "start_vm", "payload": {}})

        self.assertIn("vmName", str(context.exception))
        self.assertFalse(context.exception.retriable)

    @patch("hlvmp_worker.executor.subprocess.run")
    def test_execute_stop_vm_success(self, mock_run):
        """Test successful VM stop execution."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        job = {
            "type": "stop_vm",
            "payload": {"vmName": "test-vm"},
        }

        result = self.executor.execute_job(job)

        self.assertTrue(result["success"])
        mock_run.assert_called_once()

    def test_execute_stop_vm_missing_name(self):
        """Test stop VM requires a VM name."""
        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job({"type": "stop_vm", "payload": {}})

        self.assertIn("vmName", str(context.exception))
        self.assertFalse(context.exception.retriable)

    @patch("hlvmp_worker.executor.subprocess.run")
    def test_execute_reconcile_networking_success(self, mock_run):
        """Test successful network reconciliation execution."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        job = {
            "type": "reconcile_vm_networking",
            "payload": {"policyOnly": True},
        }

        result = self.executor.execute_job(job)

        self.assertTrue(result["success"])
        self.assertTrue(result["policyOnly"])
        mock_run.assert_called_once()
        self.assertTrue(result["policyOnly"])

    @patch("hlvmp_worker.executor.subprocess.run")
    def test_execute_reconcile_networking_defaults_policy_only_false(self, mock_run):
        """Test network reconciliation defaults to full reconcile."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = self.executor.execute_job(
            {"type": "reconcile_vm_networking", "payload": {}}
        )

        self.assertFalse(result["policyOnly"])
        mock_run.assert_called_once()

    @patch("hlvmp_worker.executor.subprocess.run")
    def test_execute_snapshot_create_success(self, mock_run):
        """Test successful snapshot creation execution."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        job = {
            "type": "snapshot_create",
            "payload": {"vmName": "test-vm"},
        }

        result = self.executor.execute_job(job)

        self.assertTrue(result["success"])
        mock_run.assert_called_once()

    def test_execute_snapshot_create_missing_name(self):
        """Test snapshot creation requires a VM name."""
        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job({"type": "snapshot_create", "payload": {}})

        self.assertIn("vmName", str(context.exception))
        self.assertFalse(context.exception.retriable)

    @patch("hlvmp_worker.executor.subprocess.run")
    def test_execute_snapshot_restore_success(self, mock_run):
        """Test successful snapshot restore execution."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = self.executor.execute_job(
            {
                "type": "snapshot_restore",
                "payload": {"vmName": "test-vm", "snapshotId": "snap-1"},
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["snapshotId"], "snap-1")
        mock_run.assert_called_once()

    def test_execute_snapshot_restore_missing_snapshot_id(self):
        """Test snapshot restore requires a snapshot ID."""
        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job(
                {"type": "snapshot_restore", "payload": {"vmName": "test-vm"}}
            )

        self.assertIn("snapshotId", str(context.exception))
        self.assertFalse(context.exception.retriable)

    @patch("hlvmp_worker.executor.subprocess.run")
    def test_execute_snapshot_delete_success(self, mock_run):
        """Test successful snapshot deletion execution."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = self.executor.execute_job(
            {
                "type": "snapshot_delete",
                "payload": {"vmName": "test-vm", "snapshotId": "snap-1"},
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["snapshotId"], "snap-1")
        mock_run.assert_called_once()

    def test_execute_snapshot_delete_missing_vm_name(self):
        """Test snapshot deletion requires a VM name."""
        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job(
                {"type": "snapshot_delete", "payload": {"snapshotId": "snap-1"}}
            )

        self.assertIn("vmName", str(context.exception))
        self.assertFalse(context.exception.retriable)

    def test_execute_snapshot_delete_missing_snapshot_id(self):
        """Test snapshot deletion requires a snapshot ID."""
        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job(
                {"type": "snapshot_delete", "payload": {"vmName": "test-vm"}}
            )

        self.assertIn("snapshotId", str(context.exception))
        self.assertFalse(context.exception.retriable)

    def test_execute_job_wraps_unexpected_handler_error(self):
        """Test unexpected handler exceptions are wrapped as retriable errors."""
        self.executor._handlers["explode"] = Mock(side_effect=RuntimeError("boom"))

        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job({"type": "explode", "payload": {}})

        self.assertIn("Job execution failed: boom", str(context.exception))
        self.assertTrue(context.exception.retriable)

    def test_execute_unsupported_job_type(self):
        """Test execution with unsupported job type."""
        job = {
            "type": "unsupported_operation",
            "payload": {},
        }

        with self.assertRaises(JobExecutionError) as context:
            self.executor.execute_job(job)

        self.assertIn("Unsupported", str(context.exception))
        self.assertFalse(context.exception.retriable)


if __name__ == "__main__":
    unittest.main()
