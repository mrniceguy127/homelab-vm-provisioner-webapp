"""Dry-run service mode for development without libvirt dependencies.

This module provides a mock implementation of the provisioner service_mode interface
that logs operations without executing them. Useful for development environments
where libvirt and other system dependencies are not available.
"""

import logging
from typing import Any

logger = logging.getLogger("dry_run_service_mode")


def create_vm(config_data: dict[str, Any], _resolved_config_path: str = "<service>", reconcile_payload: dict | None = None) -> dict[str, Any]:
    """Log VM creation without executing.

    Args:
        config_data: VM configuration data
        _resolved_config_path: Config path for logging (unused in dry-run)
        reconcile_payload: Network reconciliation payload

    Returns:
        Mock result indicating dry-run success
    """
    vm_name = config_data.get("vm", {}).get("name", "unknown")
    logger.info(f"[DRY-RUN] Would create VM: {vm_name}")
    logger.debug(f"[DRY-RUN] VM config: {config_data}")
    if reconcile_payload:
        logger.debug(f"[DRY-RUN] Reconcile payload: {reconcile_payload}")

    return {
        "success": True,
        "dry_run": True,
        "vm_name": vm_name,
        "message": "Dry-run: VM creation logged but not executed"
    }


def clone_vm(source_vm_name: str, config_data: dict[str, Any], _resolved_config_path: str = "<service>", _reconcile_payload: dict | None = None) -> dict[str, Any]:
    """Log VM cloning without executing.

    Args:
        source_vm_name: Source VM to clone from
        config_data: VM configuration data
        _resolved_config_path: Config path for logging (unused in dry-run)
        _reconcile_payload: Network reconciliation payload (unused in dry-run)

    Returns:
        Mock result indicating dry-run success
    """
    target_vm_name = config_data.get("vm", {}).get("name", "unknown")
    logger.info(f"[DRY-RUN] Would clone VM from {source_vm_name} to {target_vm_name}")
    logger.debug(f"[DRY-RUN] Target VM config: {config_data}")

    return {
        "success": True,
        "dry_run": True,
        "source_vm": source_vm_name,
        "target_vm": target_vm_name,
        "message": "Dry-run: VM cloning logged but not executed"
    }


def reconcile_vm_records(vm_records: list[dict[str, Any]], network_groups: list[dict[str, Any]] | None = None, policy_only: bool = False, allow_destructive: bool = False) -> dict[str, Any]:
    """Log network reconciliation without executing.

    Args:
        vm_records: List of VM network records
        network_groups: Optional network group definitions
        policy_only: Whether to only update policies (not infrastructure)
        allow_destructive: Whether to allow destructive changes

    Returns:
        Mock result indicating dry-run success
    """
    logger.info(f"[DRY-RUN] Would reconcile networking for {len(vm_records)} VMs")
    logger.debug(f"[DRY-RUN] Policy only: {policy_only}, Allow destructive: {allow_destructive}")
    logger.debug(f"[DRY-RUN] VM records: {vm_records}")
    if network_groups:
        logger.debug(f"[DRY-RUN] Network groups: {network_groups}")

    return {
        "success": True,
        "dry_run": True,
        "vm_count": len(vm_records),
        "policy_only": policy_only,
        "message": "Dry-run: Network reconciliation logged but not executed"
    }


def start_vm(vm_name: str) -> dict[str, Any]:
    """Log VM start without executing.

    Args:
        vm_name: Name of VM to start

    Returns:
        Mock result indicating dry-run success
    """
    logger.info(f"[DRY-RUN] Would start VM: {vm_name}")

    return {
        "success": True,
        "dry_run": True,
        "vm_name": vm_name,
        "message": "Dry-run: VM start logged but not executed"
    }


def stop_vm(vm_name: str) -> dict[str, Any]:
    """Log VM stop without executing.

    Args:
        vm_name: Name of VM to stop

    Returns:
        Mock result indicating dry-run success
    """
    logger.info(f"[DRY-RUN] Would stop VM: {vm_name}")

    return {
        "success": True,
        "dry_run": True,
        "vm_name": vm_name,
        "message": "Dry-run: VM stop logged but not executed"
    }


def destroy_vm(vm_name: str) -> dict[str, Any]:
    """Log VM destruction without executing.

    Args:
        vm_name: Name of VM to destroy

    Returns:
        Mock result indicating dry-run success
    """
    logger.info(f"[DRY-RUN] Would destroy VM: {vm_name}")

    return {
        "success": True,
        "dry_run": True,
        "vm_name": vm_name,
        "message": "Dry-run: VM destruction logged but not executed"
    }


def refresh_vm_runtime_state(vm_name: str) -> dict[str, Any]:
    """Return mock runtime state for VM.

    Args:
        vm_name: Name of VM to query

    Returns:
        Mock runtime state data
    """
    logger.info(f"[DRY-RUN] Would refresh runtime state for VM: {vm_name}")

    # Return a minimal mock state
    return {
        "vm_name": vm_name,
        "status": "unknown",
        "dry_run": True,
        "network": {
            "mac": "52:54:00:00:00:00",
            "vm_ip": "192.168.122.100",
            "bridge_name": "virbr0",
            "libvirt_network_name": "default"
        },
        "ports": [],
        "mac_address": "52:54:00:00:00:00",
        "ip_address": "192.168.122.100",
        "message": "Dry-run: Mock runtime state returned"
    }


def create_snapshot_record(vm_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Log snapshot creation without executing.

    Args:
        vm_name: Name of VM to snapshot
        payload: Snapshot creation parameters

    Returns:
        Mock snapshot metadata
    """
    snapshot_name = payload.get("snapshotName", "snapshot-1")
    logger.info(f"[DRY-RUN] Would create snapshot {snapshot_name} for VM: {vm_name}")
    logger.debug(f"[DRY-RUN] Snapshot payload: {payload}")

    return {
        "success": True,
        "dry_run": True,
        "vm_name": vm_name,
        "snapshot_name": snapshot_name,
        "metadata": {
            "disk_path": f"/var/lib/libvirt/images/{vm_name}-snapshot.qcow2",
            "state_path": f"/var/lib/libvirt/images/{vm_name}-snapshot.state"
        },
        "message": "Dry-run: Snapshot creation logged but not executed"
    }


def restore_snapshot_record(vm_name: str, snapshot_id: int, metadata: dict[str, Any], _vm_records: list[dict[str, Any]] | None = None, _network_groups: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Log snapshot restoration without executing.

    Args:
        vm_name: Name of VM to restore
        snapshot_id: Snapshot ID
        metadata: Snapshot metadata
        _vm_records: Optional VM records for network reconciliation (unused in dry-run)
        _network_groups: Optional network group definitions (unused in dry-run)

    Returns:
        Mock result indicating dry-run success
    """
    logger.info(f"[DRY-RUN] Would restore snapshot {snapshot_id} for VM: {vm_name}")
    logger.debug(f"[DRY-RUN] Snapshot metadata: {metadata}")

    return {
        "success": True,
        "dry_run": True,
        "vm_name": vm_name,
        "snapshot_id": snapshot_id,
        "message": "Dry-run: Snapshot restoration logged but not executed"
    }


def delete_snapshot_record(vm_name: str, snapshot_id: int, metadata: dict[str, Any]) -> dict[str, Any]:
    """Log snapshot deletion without executing.

    Args:
        vm_name: Name of VM
        snapshot_id: Snapshot ID to delete
        metadata: Snapshot metadata

    Returns:
        Mock result indicating dry-run success
    """
    logger.info(f"[DRY-RUN] Would delete snapshot {snapshot_id} for VM: {vm_name}")
    logger.debug(f"[DRY-RUN] Snapshot metadata: {metadata}")

    return {
        "success": True,
        "dry_run": True,
        "vm_name": vm_name,
        "snapshot_id": snapshot_id,
        "message": "Dry-run: Snapshot deletion logged but not executed"
    }
