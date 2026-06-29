# Homelab VM Provisioner Worker - AGENTS.md

Long-running daemon for processing VM provisioning jobs from PostgreSQL.

## Project Role

The worker is a **standalone Python service** that claims and executes queued provisioning jobs. It runs outside the API request path and communicates with the database microservice via HTTP REST API. The worker calls `vmctl` as a subprocess rather than importing provisioner code directly.

##Quick Start

```bash
./setup                # Install dependencies
cp .env.example .env   # Configure environment
./start                # Start worker daemon
```

## Configuration

Environment variables (set in `.env`):
- `HOST_ID`: Host identifier for job claiming (required)
- `DB_SERVICE_URL`: Database microservice URL (required)
- `DB_SERVICE_PASSWORD`: Database microservice password (required)
- `PROVISIONER_CLI_PATH`: Path to provisioner CLI directory (default: PATH lookup)
- `WORKER_ID`: Unique worker identifier (default: auto-generated)
- `PROVISIONER_CONCURRENCY`: Max concurrent jobs (default: 1)
- `WORKER_POLL_INTERVAL`: Poll interval in seconds (default: 5.0)
- `WORKER_DRY_RUN`: Enable dry-run mode (default: false, auto-enables if dependencies unavailable)

### Dry-Run Mode

The worker automatically falls back to dry-run mode when system dependencies (libvirt, nftables) are unavailable. In dry-run mode:
- Operations are logged but not executed
- Jobs complete successfully without making system changes
- No sudo privileges required
- Ideal for development without VM infrastructure

Enable explicitly with `WORKER_DRY_RUN=true` or let it auto-detect missing dependencies.

## Testing

```bash
./setup --dev  # Install dev dependencies
.venv/bin/python -m unittest discover -s tests
```

## Key Design Points

- **In-Process Execution**: Imports and calls provisioner service module directly
- **HTTP Client**: Uses database microservice REST API (not direct PostgreSQL)
- **Resource Locking**: Prevents conflicting concurrent operations
- **Concurrency Support**: Thread pool for concurrent job execution
- **Graceful Shutdown**: Waits for active jobs to complete
- **Dry-Run Mode**: Auto-detects missing dependencies and logs operations without executing
- **Cannot be Dockerized**: Must run on host for libvirt access (or use dry-run mode)

## Module Structure

```
hlvmp_worker/
├── config.py              # Worker configuration from environment
├── db_client.py           # HTTP client for database microservice
├── executor.py            # Job executor (service module-based)
├── dry_run_service_mode.py # Mock service mode for dry-run
└── worker.py              # Main daemon with event loop
```

## Integration Modes

### Monorepo Mode
Set `PROVISIONER_CLI_PATH=../homelab-vm-provisioner-cli`

### Standalone Mode
Ensure `vmctl` is in PATH or set `PROVISIONER_CLI_PATH`

## Code Style

- Python 3.9+
- unittest (NOT pytest)
- ruff for linting
- Google-style docstrings
- Type hints where beneficial
