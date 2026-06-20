"""Job executor for provisioner operations.

Maps job types to provisioner CLI commands and handles execution via subprocess.
"""

import subprocess
from pathlib import Path
from typing import Any, Callable


class JobExecutionError(Exception):
    """Raised when job execution fails."""

    def __init__(self, message: str, retriable: bool = False):
        """Initialize job execution error.

        Args:
            message: Error message
            retriable: Whether the job can be retried
        """
        super().__init__(message)
        self.retriable = retriable


class JobExecutor:
    """Executes provisioner jobs by calling vmctl subprocess."""

    def __init__(self, provisioner_cli_path: str):
        """Initialize job executor.

        Args:
            provisioner_cli_path: Path to provisioner CLI directory
        """
        self.provisioner_cli_path = Path(provisioner_cli_path)
        self.vmctl_path = self.provisioner_cli_path / "vmctl"

        if not self.vmctl_path.exists():
            raise ValueError(f"vmctl not found at {self.vmctl_path}")

        self._handlers: dict[str, Callable] = {
            "provision_vm": self._execute_provision_vm,
            "destroy_vm": self._execute_destroy_vm,
            "clone_vm": self._execute_clone_vm,
            "start_vm": self._execute_start_vm,
            "stop_vm": self._execute_stop_vm,
            "reconcile_vm_networking": self._execute_reconcile_networking,
            "snapshot_create": self._execute_snapshot_create,
            "snapshot_restore": self._execute_snapshot_restore,
            "snapshot_delete": self._execute_snapshot_delete,
        }

    def _run_vmctl(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run vmctl command.

        Args:
            *args: Command arguments
            check: Raise exception on non-zero exit

        Returns:
            CompletedProcess instance

        Raises:
            JobExecutionError: If command fails and check=True
        """
        cmd = [str(self.vmctl_path), *list(args)]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.provisioner_cli_path),
                capture_output=True,
                text=True,
                check=False,
            )

            if check and result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip() or f"Command failed with exit code {result.returncode}"
                raise JobExecutionError(
                    f"vmctl command failed: {error_msg}",
                    retriable=True
                )

            return result

        except JobExecutionError:
            raise
        except FileNotFoundError as e:
            raise JobExecutionError(
                f"vmctl not found: {e}",
                retriable=False
            ) from e
        except Exception as e:
            raise JobExecutionError(
                f"Failed to execute vmctl: {e}",
                retriable=True
            ) from e

    def get_supported_job_types(self) -> list[str]:
        """Get list of supported job types.

        Returns:
            List of job type strings
        """
        return list(self._handlers.keys())

    def get_resource_locks(self, job: dict[str, Any]) -> list[str]:
        """Determine resource locks required for a job.

        Args:
            job: Job data dictionary

        Returns:
            List of lock keys required for this job
        """
        job_type = job["type"]
        target_host_id = job["targetHostId"]
        target_vm_id = job.get("targetVmId")

        locks = []

        # VM-specific mutation jobs lock the VM
        if job_type in (
            "provision_vm",
            "destroy_vm",
            "clone_vm",
            "start_vm",
            "stop_vm",
            "snapshot_create",
            "snapshot_restore",
            "snapshot_delete",
        ):
            if target_vm_id:
                locks.append(f"vm:{target_vm_id}")
            else:
                # Fallback to host lock if VM ID is missing
                locks.append(f"host:{target_host_id}")

        # Network reconciliation locks firewall and network
        elif job_type == "reconcile_vm_networking":
            locks.append(f"firewall:{target_host_id}")
            locks.append(f"network:{target_host_id}")

        # Default to host lock for unknown job types
        else:
            locks.append(f"host:{target_host_id}")

        # Sort locks for deterministic ordering (prevent deadlocks)
        return sorted(locks)

    def execute_job(self, job: dict[str, Any]) -> dict[str, Any]:
        """Execute a job based on its type.

        Args:
            job: Job data dictionary with type, payload, etc.

        Returns:
            Job result data

        Raises:
            JobExecutionError: If job execution fails
        """
        job_type = job["type"]
        payload = job.get("payload", {})

        handler = self._handlers.get(job_type)
        if not handler:
            raise JobExecutionError(
                f"Unsupported job type: {job_type}", retriable=False
            )

        try:
            return handler(payload)
        except JobExecutionError:
            raise
        except Exception as e:
            raise JobExecutionError(
                f"Job execution failed: {e}", retriable=True
            ) from e

    def _execute_provision_vm(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute VM provision job.

        Args:
            payload: Job payload with configPath

        Returns:
            Job result data

        Raises:
            JobExecutionError: If provision fails
        """
        config_path = payload.get("configPath")
        if not config_path:
            raise JobExecutionError(
                "Missing required field: configPath", retriable=False
            )

        config_path_obj = Path(config_path)
        if not config_path_obj.exists():
            raise JobExecutionError(
                f"Config file not found: {config_path}", retriable=False
            )

        self._run_vmctl("create", config_path)
        return {
            "success": True,
            "configPath": config_path,
            "message": "VM provisioned successfully",
        }

    def _execute_destroy_vm(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute VM destroy job.

        Args:
            payload: Job payload with vmName

        Returns:
            Job result data

        Raises:
            JobExecutionError: If destroy fails
        """
        vm_name = payload.get("vmName")
        if not vm_name:
            raise JobExecutionError(
                "Missing required field: vmName", retriable=False
            )

        self._run_vmctl("destroy", vm_name)
        return {
            "success": True,
            "vmName": vm_name,
            "message": "VM destroyed successfully",
        }

    def _execute_clone_vm(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute VM clone job.

        Args:
            payload: Job payload with sourceVmName and configPath

        Returns:
            Job result data

        Raises:
            JobExecutionError: If clone fails
        """
        source_vm_name = payload.get("sourceVmName")
        config_path = payload.get("configPath")

        if not source_vm_name:
            raise JobExecutionError(
                "Missing required field: sourceVmName", retriable=False
            )
        if not config_path:
            raise JobExecutionError(
                "Missing required field: configPath", retriable=False
            )

        config_path_obj = Path(config_path)
        if not config_path_obj.exists():
            raise JobExecutionError(
                f"Config file not found: {config_path}", retriable=False
            )

        self._run_vmctl("clone", source_vm_name, config_path)
        return {
            "success": True,
            "sourceVmName": source_vm_name,
            "configPath": config_path,
            "message": "VM cloned successfully",
        }

    def _execute_start_vm(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute VM start job.

        Args:
            payload: Job payload with vmName

        Returns:
            Job result data

        Raises:
            JobExecutionError: If start fails
        """
        vm_name = payload.get("vmName")
        if not vm_name:
            raise JobExecutionError(
                "Missing required field: vmName", retriable=False
            )

        self._run_vmctl("start", vm_name)
        return {
            "success": True,
            "vmName": vm_name,
            "message": "VM started successfully",
        }

    def _execute_stop_vm(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute VM stop job.

        Args:
            payload: Job payload with vmName

        Returns:
            Job result data

        Raises:
            JobExecutionError: If stop fails
        """
        vm_name = payload.get("vmName")
        if not vm_name:
            raise JobExecutionError(
                "Missing required field: vmName", retriable=False
            )

        self._run_vmctl("stop", vm_name)
        return {
            "success": True,
            "vmName": vm_name,
            "message": "VM stopped successfully",
        }

    def _execute_reconcile_networking(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute network reconciliation job.

        Args:
            payload: Job payload with optional policyOnly flag

        Returns:
            Job result data

        Raises:
            JobExecutionError: If reconciliation fails
        """
        policy_only = payload.get("policyOnly", False)

        args = ["reconcile"]
        if policy_only:
            args.append("--policy-only")

        self._run_vmctl(*args)
        return {
            "success": True,
            "policyOnly": policy_only,
            "message": "Network reconciliation completed successfully",
        }

    def _execute_snapshot_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute snapshot creation job.

        Args:
            payload: Job payload with vmName

        Returns:
            Job result data

        Raises:
            JobExecutionError: If snapshot creation fails
        """
        vm_name = payload.get("vmName")
        if not vm_name:
            raise JobExecutionError(
                "Missing required field: vmName", retriable=False
            )

        self._run_vmctl("snapshot-create", vm_name)
        return {
            "success": True,
            "vmName": vm_name,
            "message": "Snapshot created successfully",
        }

    def _execute_snapshot_restore(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute snapshot restore job.

        Args:
            payload: Job payload with vmName and snapshotId

        Returns:
            Job result data

        Raises:
            JobExecutionError: If snapshot restore fails
        """
        vm_name = payload.get("vmName")
        snapshot_id = payload.get("snapshotId")

        if not vm_name:
            raise JobExecutionError(
                "Missing required field: vmName", retriable=False
            )
        if not snapshot_id:
            raise JobExecutionError(
                "Missing required field: snapshotId", retriable=False
            )

        self._run_vmctl("snapshot-restore", vm_name, snapshot_id)
        return {
            "success": True,
            "vmName": vm_name,
            "snapshotId": snapshot_id,
            "message": "Snapshot restored successfully",
        }

    def _execute_snapshot_delete(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute snapshot deletion job.

        Args:
            payload: Job payload with vmName and snapshotId

        Returns:
            Job result data

        Raises:
            JobExecutionError: If snapshot deletion fails
        """
        vm_name = payload.get("vmName")
        snapshot_id = payload.get("snapshotId")

        if not vm_name:
            raise JobExecutionError(
                "Missing required field: vmName", retriable=False
            )
        if not snapshot_id:
            raise JobExecutionError(
                "Missing required field: snapshotId", retriable=False
            )

        self._run_vmctl("snapshot-delete", vm_name, snapshot_id)
        return {
            "success": True,
            "vmName": vm_name,
            "snapshotId": snapshot_id,
            "message": "Snapshot deleted successfully",
        }
