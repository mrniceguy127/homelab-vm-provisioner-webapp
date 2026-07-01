# Homelab VM Provisioner Worker - AGENTS.md

Long-running daemon that consumes VM provisioning jobs from RabbitMQ and executes them.

## Project Role

The worker is a **standalone Python service** that consumes queued provisioning jobs from its host-specific RabbitMQ queue and executes them. It runs outside the API request path, fetches job details from the API, and manages job metadata, events, and resource locks through the database microservice via HTTP REST API. The worker calls `vmctl` as a subprocess rather than importing provisioner code directly.

##Quick Start

```bash
./setup                # Install dependencies
cp .env.example .env   # Configure environment
./start                # Start worker daemon
```

## Configuration

Environment variables (set in `.env`):
- `HOST_ID`: Host identifier; selects the queue and matches job routing (required)
- `QUEUE_HOST`: RabbitMQ host (required)
- `QUEUE_PORT`: RabbitMQ AMQP port (default: 3334)
- `QUEUE_VHOST`: RabbitMQ virtual host (default: provisioner)
- `QUEUE_NAME`: Host-specific queue to consume (default: provisioner.worker.<HOST_ID>)
- `QUEUE_USER` / `QUEUE_PASSWORD`: Consume-only RabbitMQ credentials
- `API_HOST` / `API_PORT`: API used to fetch/update job details (required)
- `DB_SERVICE_HOST`: Database microservice host (required)
- `DB_SERVICE_PORT`: Database microservice port (default: 3002)
- `DB_SERVICE_PASSWORD`: Database microservice password (required)
- `PROVISIONER_CLI_PATH`: Path to provisioner CLI directory (required; must be set explicitly)
- `WORKER_ID`: Unique worker identifier (default: auto-generated)
- `PROVISIONER_CONCURRENCY`: Max concurrent jobs (default: 1)
- `WORKER_STATE_REFRESH_INTERVAL`: Runtime-state refresh interval in seconds (default: 60.0)
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

- **RabbitMQ Consumption**: Consumes jobs from a host-specific queue (pull model, not polling)
- **Subprocess Execution**: Runs the `vmctl` CLI as a subprocess (does not import provisioner code)
- **HTTP Client**: Uses the database microservice REST API (not direct PostgreSQL) and the API for job details
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
├── rabbitmq_consumer.py   # RabbitMQ consumer (job delivery)
├── executor.py            # Job executor (subprocess-based vmctl calls)
├── dry_run_service_mode.py # Mock service mode for dry-run
└── worker.py              # Main daemon with event loop
```

## Integration Modes

### Monorepo Mode
Set `PROVISIONER_CLI_PATH=../homelab-vm-provisioner-cli`

### Standalone Mode
Set `PROVISIONER_CLI_PATH` to the provisioner CLI checkout (required)

## Code Style

- Python 3.9+
- unittest (NOT pytest)
- ruff for linting
- Google-style docstrings
- Type hints where beneficial
