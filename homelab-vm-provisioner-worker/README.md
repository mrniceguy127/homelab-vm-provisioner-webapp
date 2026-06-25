# Homelab VM Provisioner Worker

Long-running daemon for processing VM provisioning jobs from PostgreSQL.

## Overview

The worker daemon is a standalone Python service that claims and executes queued provisioning jobs. It is designed to run on the same host as the VMs being provisioned and must have access to the `vmctl` command-line tool from the [homelab-vm-provisioner-cli](../homelab-vm-provisioner-cli) project.

## Features

- Claims jobs only for configured `HOST_ID` (never processes other hosts' jobs)
- Concurrent job execution (configurable via `PROVISIONER_CONCURRENCY`)
- Resource locking prevents conflicting concurrent operations
- Graceful shutdown (waits for active jobs to complete)
- Automatic retry for transient failures
- Comprehensive event logging per job

## Quick Start

```bash
# Setup (install dependencies)
./setup

# Configure environment
cp .env.example .env
# Edit .env and set HOST_ID, DB_SERVICE_URL, DB_SERVICE_PASSWORD

# Start worker (requires sudo for libvirt/nftables access)
./start
```

**Note**: The worker requires sudo access to execute provisioner CLI operations that interact with libvirt and nftables. You will be prompted for your sudo password on startup.

## Configuration

The worker reads configuration from environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HOST_ID` | Yes | - | Host identifier for job claiming |
| `DB_SERVICE_URL` | Yes | - | Database microservice URL |
| `DB_SERVICE_PASSWORD` | Yes | - | Database microservice password |
| `PROVISIONER_CLI_PATH` | No | PATH lookup | Path to provisioner CLI directory |
| `WORKER_ID` | No | auto-generated | Unique worker identifier (hostname-PID) |
| `PROVISIONER_CONCURRENCY` | No | 1 | Maximum concurrent jobs |
| `WORKER_POLL_INTERVAL` | No | 5.0 | Poll interval in seconds |

### Monorepo Configuration

When running in the monorepo, set `PROVISIONER_CLI_PATH` to point to the local provisioner CLI:

```bash
PROVISIONER_CLI_PATH=../homelab-vm-provisioner-cli
```

This allows the worker to use the monorepo's provisioner without requiring it to be installed system-wide.

## Supported Job Types

- `provision_vm`: Create a new VM from a config file
- `destroy_vm`: Destroy an existing VM
- `clone_vm`: Clone a VM disk to create a new VM
- `start_vm`: Start a stopped VM
- `stop_vm`: Stop a running VM
- `reconcile_vm_networking`: Reconcile network configuration and firewall rules
- `snapshot_create`: Create a VM snapshot
- `snapshot_restore`: Restore a VM from a snapshot
- `snapshot_delete`: Delete a VM snapshot

## Resource Locking

The worker uses resource locks to prevent concurrent operations on the same resource:

- **VM locks** (`vm:<vm_id>`): Lock specific VMs during mutation operations
- **Host locks** (`host:<host_id>`): Lock entire host for host-level operations
- **Firewall locks** (`firewall:<host_id>`): Lock firewall during network reconciliation
- **Network locks** (`network:<host_id>`): Lock network during network reconciliation

Locks are sorted alphabetically for deterministic ordering to prevent deadlocks.

## Concurrency

The worker supports concurrent job execution up to `PROVISIONER_CONCURRENCY`:

- Jobs for different VMs can run concurrently
- Jobs requiring the same locks are serialized
- Failed lock acquisition causes job retry (not failure)

**Recommendation**: Start with `PROVISIONER_CONCURRENCY=1` and increase cautiously. Concurrent provisioning can be resource-intensive.

## Testing

Run tests:

```bash
# Run all tests
./scripts/test

# Run tests with coverage (requires 80% minimum)
./scripts/coverage

# Run specific test module
.venv/bin/python -m unittest tests.test_worker
```

**Coverage requirement**: The project enforces 80% minimum test coverage. The `./scripts/coverage` script will fail if coverage drops below this threshold.

## Deployment

### Standalone Deployment

The worker can be deployed independently on any host:

1. Install the worker: `./setup`
2. Configure environment variables in `.env`
3. Ensure `vmctl` is in PATH or set `PROVISIONER_CLI_PATH`
4. Start the worker: `./start`

### Monorepo Deployment

When running as part of the monorepo:

1. Configure `.env` with `PROVISIONER_CLI_PATH=../homelab-vm-provisioner-cli`
2. Use monorepo scripts: `./start --enable-worker` (from workspace root)

### Systemd Service (Future)

The worker is designed to run as a systemd service. Service file will be added in a future update.

## Architecture

```
Worker Daemon
   ↓ (claims jobs)
Database Microservice
   ↓ (queries)
PostgreSQL
```

The worker:
1. Polls database microservice for queued jobs matching `HOST_ID`
2. Claims jobs using row-level locking (safe for concurrent workers)
3. Acquires resource locks before execution
4. Executes job by calling `vmctl` command
5. Updates job status and appends events
6. Releases resource locks

## Limitations

- Cannot be dockerized (must run on host for libvirt access)
- Requires RabbitMQ for job consumption
- No automatic stale job recovery (manual intervention required)
- No authentication/authorization (assumes trusted environment)

## Development

Project structure:

```
hlvmp_worker/
  ├── __init__.py
  ├── config.py        # Configuration management
  ├── db_client.py     # Database microservice client
  ├── executor.py      # Job executor (calls vmctl)
  └── worker.py        # Main worker daemon

tests/
  ├── test_config.py
  ├── test_db_client.py
  ├── test_executor.py
  └── test_worker.py
```

---

# Job Execution Flow

## Overview

```
1. Worker consumes job message from RabbitMQ queue (host-specific queue)
2. Worker validates job targets this host (target_host_id matches HOST_ID)
3. Worker fetches full job details from API (/internal/worker/jobs/:id)
4. Worker marks job as running via API (/internal/worker/jobs/:id/start)
5. Worker acquires resource locks (vm:<name>, network:<host>, etc.)
6. Worker executes vmctl command (provision, destroy, start, stop, etc.)
7. Worker captures stdout/stderr and appends events to job log
8. Worker marks job as succeeded or failed via API
9. Worker releases resource locks
10. Worker ACKs RabbitMQ message (or NACKs on failure)
11. Worker continues consuming next message from queue
```

## Job Type to Command Mapping

| Job Type | vmctl Command | Locks Required |
|----------|---------------|----------------|
| `provision_vm` | `vmctl create <config>` | `vm:<name>`, `network:<host>`, `firewall:<host>` |
| `destroy_vm` | `vmctl destroy <name>` | `vm:<name>`, `network:<host>`, `firewall:<host>` |
| `clone_vm` | `vmctl clone <source> <config>` | `vm:<source>`, `vm:<target>`, `network:<host>`, `firewall:<host>` |
| `start_vm` | `vmctl start <name>` | `vm:<name>` |
| `stop_vm` | `vmctl stop <name>` | `vm:<name>` |
| `reconcile_vm_networking` | `vmctl reconcile` | `network:<host>`, `firewall:<host>` |
| `snapshot_create` | `vmctl snapshot-create <name>` | `vm:<name>` |
| `snapshot_restore` | `vmctl snapshot-restore <name> <id>` | `vm:<name>`, `network:<host>`, `firewall:<host>` |
| `snapshot_delete` | `vmctl snapshot-delete <name> <id>` | `vm:<name>` |

## Resource Locking

### Lock Types

- **VM Lock** (`vm:<name>`): Prevents concurrent operations on the same VM
- **Network Lock** (`network:<host>`): Prevents concurrent network config changes
- **Firewall Lock** (`firewall:<host>`): Prevents concurrent nftables changes
- **Host Lock** (`host:<host>`): Locks entire host for host-level operations

### Lock Acquisition

Locks are acquired before job execution:

1. Worker requests locks from database service
2. Database uses PostgreSQL `FOR UPDATE SKIP LOCKED` for safe concurrent claiming
3. If locks are held by another job, acquisition fails
4. Worker retries job later (does not mark as failed)
5. Locks have TTL (default 5 minutes) and expire automatically

### Lock Ordering

To prevent deadlocks, locks are always acquired in alphabetical order:

```python
locks = sorted(['vm:devbox', 'network:local', 'firewall:local'])
# Result: ['firewall:local', 'network:local', 'vm:devbox']
```

## Event Logging

The worker appends events to the job log throughout execution:

```python
# Job claimed
await db.append_event(job_id, 'info', 'Job claimed by worker', {'worker_id': worker_id})

# Locks acquired
await db.append_event(job_id, 'info', 'Acquired locks', {'locks': lock_keys})

# Command started
await db.append_event(job_id, 'info', 'Executing vmctl command', {'command': cmd})

# Command output
await db.append_event(job_id, 'debug', 'Command stdout', {'output': stdout})

# Command completed
await db.append_event(job_id, 'info', 'Command completed', {'exit_code': 0, 'duration_ms': 5000})

# Locks released
await db.append_event(job_id, 'info', 'Released locks', {'locks': lock_keys})
```

Event levels: `debug`, `info`, `warning`, `error`

## Error Handling

### Retriable Errors

Jobs are retried up to `max_attempts` times for transient errors:
- Lock acquisition failure
- Network timeout
- Temporary filesystem issues

### Non-Retriable Errors

Jobs fail immediately and are not retried:
- Invalid config (VM name already exists, invalid network config)
- Missing resources (source VM not found for clone)
- Permission denied (sudo password required)

### Failed Job Handling

When a job fails:
1. Worker captures error message and stderr
2. Worker marks job as failed with error details
3. Worker appends error event to job log
4. Worker releases any acquired locks
5. Job status becomes `failed` and is not retried if `attempts >= max_attempts`

## Concurrency

The worker supports concurrent job execution via `PROVISIONER_CONCURRENCY`:

```bash
# Run up to 3 jobs concurrently
PROVISIONER_CONCURRENCY=3
```

### Concurrency Rules

- Jobs for different VMs can run concurrently
- Jobs requiring the same locks are serialized
- Resource locks prevent conflicts
- Workers poll independently and use row-level locking to claim jobs

### Recommendations

- Start with `PROVISIONER_CONCURRENCY=1` for stability
- Increase cautiously based on host resources
- Monitor CPU, memory, and disk I/O
- Provisioning is I/O-intensive (disk copying, network setup)

## Graceful Shutdown

The worker handles SIGTERM and SIGINT gracefully:

1. Stop consuming new messages from RabbitMQ
2. Close RabbitMQ connection
3. Exit

Active jobs complete normally during shutdown. RabbitMQ will requeue any unACKed messages automatically.

## Monitoring

### Worker Status

Check worker process:

```bash
# Is worker running?
ps aux | grep hlvmp_worker

# Check logs
journalctl -u hlvmp-worker -f
```

### Job Status

Query database service:

```bash
# All jobs for host
curl -H "Authorization: Bearer $DB_SERVICE_PASSWORD" \
  "http://localhost:3002/jobs?targetHostId=local"

# Specific job
curl -H "Authorization: Bearer $DB_SERVICE_PASSWORD" \
  "http://localhost:3002/jobs/123"

# Job events
curl -H "Authorization: Bearer $DB_SERVICE_PASSWORD" \
  "http://localhost:3002/jobs/123/events"
```

### Lock Status

Check active locks:

```sql
SELECT * FROM resource_locks WHERE expires_at > NOW();
```

Cleanup expired locks:

```bash
curl -X POST \
  -H "Authorization: Bearer $DB_SERVICE_PASSWORD" \
  "http://localhost:3002/locks/cleanup"
```

## Troubleshooting

### Worker Not Claiming Jobs

**Problem**: Jobs stay in `queued` status

**Solutions**:
- Verify worker is running: `ps aux | grep hlvmp_worker`
- Check `HOST_ID` matches job's `target_host_id`
- Verify database connection: `curl http://localhost:3002/health`
- Check worker logs for errors

### Jobs Stuck in Running

**Problem**: Jobs marked as `running` but never complete

**Solutions**:
- Check if worker crashed: `ps aux | grep hlvmp_worker`
- Inspect job events: `GET /jobs/:id/events`
- Check vmctl process: `ps aux | grep vmctl`
- Manually cleanup stale locks: `POST /locks/cleanup`
- Restart worker

### Permission Denied Errors

**Problem**: Worker fails with "permission denied" errors

**Solutions**:
- Verify worker runs with sudo access
- Check libvirt socket permissions: `ls -la /var/run/libvirt/`
- Add user to libvirt group: `sudo usermod -a -G libvirt $USER`
- Verify nftables permissions (requires sudo)

### Lock Acquisition Failures

**Problem**: Jobs fail with "failed to acquire locks"

**Solutions**:
- Check for stuck locks: `SELECT * FROM resource_locks;`
- Cleanup expired locks: `POST /locks/cleanup`
- Reduce `PROVISIONER_CONCURRENCY` to avoid contention
- Wait for conflicting jobs to complete

### High CPU/Memory Usage

**Problem**: Worker consumes excessive resources

**Solutions**:
- Reduce `PROVISIONER_CONCURRENCY`
- Check for runaway vmctl processes: `ps aux | grep vmctl`
- Monitor disk I/O during provisioning
- Increase VM host resources

## License

MIT

