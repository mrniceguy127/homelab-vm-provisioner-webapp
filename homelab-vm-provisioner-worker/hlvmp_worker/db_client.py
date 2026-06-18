"""Database client for job queue operations.

Communicates with the database microservice via HTTP REST API.
"""

import json
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DatabaseClient:
    """Client for database microservice operations."""

    def __init__(self, base_url: str, password: str):
        """Initialize database client.

        Args:
            base_url: Base URL of database microservice
            password: Authentication password for database microservice
        """
        self.base_url = base_url.rstrip("/")
        self.password = password

    def _request(
        self, method: str, path: str, data: Optional[dict[str, Any]] = None
    ) -> Any:
        """Make HTTP request to database microservice.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (without base URL)
            data: Optional request body data

        Returns:
            Response data (parsed JSON)

        Raises:
            RuntimeError: If request fails
        """
        url = f"{self.base_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.password}",
        }

        body = json.dumps(data).encode("utf-8") if data else None

        request = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(request, timeout=10) as response:
                response_data = response.read().decode("utf-8")
                if response_data:
                    return json.loads(response_data)
                return None
        except HTTPError as e:
            error_body = e.read().decode("utf-8")
            try:
                error_data = json.loads(error_body)
                error_message = error_data.get("error", error_body)
            except json.JSONDecodeError:
                error_message = error_body

            raise RuntimeError(
                f"Database request failed: {method} {path} - "
                f"Status {e.code}: {error_message}"
            ) from e
        except URLError as e:
            raise RuntimeError(
                f"Failed to connect to database microservice at {url}: {e.reason}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Database request error: {e}") from e

    def health_check(self) -> bool:
        """Check if database microservice is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self._request("GET", "/health")
            return response.get("status") == "ok"
        except Exception:
            return False

    def claim_next_job(self, target_host_id: str, worker_id: str) -> Optional[dict[str, Any]]:
        """Claim the next available job for a host.

        Args:
            target_host_id: Host ID to claim job for
            worker_id: Worker ID claiming the job

        Returns:
            Claimed job data or None if no jobs available

        Raises:
            RuntimeError: If claim operation fails
        """
        try:
            response = self._request(
                "POST",
                "/jobs/claim",
                {"targetHostId": target_host_id, "workerId": worker_id},
            )
            return response.get("job")
        except RuntimeError as e:
            if "404" in str(e):
                return None
            raise

    def mark_job_running(self, job_id: int, worker_id: str) -> dict[str, Any]:
        """Mark a job as running.

        Args:
            job_id: Job ID
            worker_id: Worker ID running the job

        Returns:
            Updated job data

        Raises:
            RuntimeError: If update fails
        """
        response = self._request(
            "PUT", f"/jobs/{job_id}/status", {"status": "running", "workerId": worker_id}
        )
        return response["job"]

    def mark_job_succeeded(self, job_id: int, result: dict[str, Any]) -> dict[str, Any]:
        """Mark a job as succeeded.

        Args:
            job_id: Job ID
            result: Job result data

        Returns:
            Updated job data

        Raises:
            RuntimeError: If update fails
        """
        response = self._request(
            "PUT", f"/jobs/{job_id}/status", {"status": "succeeded", "result": result}
        )
        return response["job"]

    def mark_job_failed(
        self, job_id: int, error: str, retriable: bool = False
    ) -> dict[str, Any]:
        """Mark a job as failed.

        Args:
            job_id: Job ID
            error: Error message
            retriable: Whether job can be retried

        Returns:
            Updated job data

        Raises:
            RuntimeError: If update fails
        """
        response = self._request(
            "PUT",
            f"/jobs/{job_id}/status",
            {"status": "failed", "error": error, "retriable": retriable},
        )
        return response["job"]

    def append_job_event(
        self,
        job_id: int,
        level: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Append an event to a job's log.

        Args:
            job_id: Job ID
            level: Event level (debug, info, warning, error)
            message: Event message
            metadata: Optional event metadata

        Returns:
            Created event data

        Raises:
            RuntimeError: If append fails
        """
        response = self._request(
            "POST",
            f"/jobs/{job_id}/events",
            {"level": level, "message": message, "metadata": metadata},
        )
        return response["event"]

    def acquire_resource_locks(
        self,
        job_id: int,
        worker_id: str,
        lock_keys: list[str],
        ttl_ms: int = 300000,
    ) -> bool:
        """Acquire resource locks for a job.

        Args:
            job_id: Job ID
            worker_id: Worker ID
            lock_keys: List of resource keys to lock
            ttl_ms: Lock TTL in milliseconds (default: 300000 = 5 minutes)

        Returns:
            True if all locks acquired, False otherwise

        Raises:
            RuntimeError: If lock operation fails
        """
        try:
            response = self._request(
                "POST",
                "/locks/acquire",
                {
                    "jobId": job_id,
                    "workerId": worker_id,
                    "lockKeys": lock_keys,
                    "ttlMs": ttl_ms,
                },
            )
            return response.get("acquired", False)
        except RuntimeError as e:
            if "409" in str(e) or "conflict" in str(e).lower():
                return False
            raise

    def release_resource_locks(self, job_id: int, worker_id: str) -> int:
        """Release all resource locks for a job.

        Args:
            job_id: Job ID
            worker_id: Worker ID (optional, for verification)

        Returns:
            Number of locks released

        Raises:
            RuntimeError: If release operation fails
        """
        response = self._request(
            "DELETE", f"/locks/job/{job_id}", {"workerId": worker_id}
        )
        return response.get("released", 0)

    def list_jobs(
        self,
        status: Optional[str] = None,
        target_host_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List jobs with optional filtering.

        Args:
            status: Filter by status (queued, running, succeeded, failed)
            target_host_id: Filter by target host ID
            limit: Maximum number of results

        Returns:
            List of job data

        Raises:
            RuntimeError: If list operation fails
        """
        params = []
        if status:
            params.append(f"status={status}")
        if target_host_id:
            params.append(f"targetHostId={target_host_id}")
        params.append(f"limit={limit}")

        query_string = "?" + "&".join(params) if params else ""
        response = self._request("GET", f"/jobs{query_string}")
        return response.get("jobs", [])
