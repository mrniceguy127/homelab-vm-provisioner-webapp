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

## Testing

```bash
./setup --dev  # Install dev dependencies
.venv/bin/python -m unittest discover -s tests
```

## Key Design Points

- **Subprocess Execution**: Calls `vmctl` command instead of importing provisioner
- **HTTP Client**: Uses database microservice REST API (not direct PostgreSQL)
- **Resource Locking**: Prevents conflicting concurrent operations
- **Concurrency Support**: Thread pool for concurrent job execution
- **Graceful Shutdown**: Waits for active jobs to complete
- **Cannot be Dockerized**: Must run on host for libvirt access

## Module Structure

```
hlvmp_worker/
├── config.py         # Worker configuration from environment
├── db_client.py      # HTTP client for database microservice
├── executor.py       # Job executor (subprocess-based vmctl calls)
└── worker.py         # Main daemon with event loop
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
