# Homelab VM Provisioner Database (PostgreSQL)

PostgreSQL infrastructure component for the provisioner. It owns the database
engine and the SQL schema (migrations) that store job metadata, event logs,
resource locks, and VM records.

This component is **PostgreSQL only** — it does not run the HTTP API. The REST
interface in front of this database lives in
[homelab-vm-provisioner-db-interface](../homelab-vm-provisioner-db-interface).
Job **delivery** is handled by RabbitMQ
([homelab-vm-provisioner-job-queue](../homelab-vm-provisioner-job-queue)).

Like the other infrastructure components, it exposes lifecycle scripts:
`setup`, `start`, `stop`, `build`, and `test`.

## Quick Start

```bash
# Native PostgreSQL (default, recommended for production)
./setup              # Install PostgreSQL server and client
./start              # Start the PostgreSQL service

# Create database and user (first install only)
sudo -u postgres psql -c "CREATE DATABASE hlvmp;"
sudo -u postgres psql -c "CREATE USER hlvmp WITH PASSWORD 'hlvmppass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE hlvmp TO hlvmp;"

./build              # Run migrations (schema provisioning)
./test               # Verify connectivity + schema

# Stop
./stop

# Docker mode (development)
./setup --docker     # Pull postgres image
./build --docker     # Build hlvmp-db image (postgres + migrations)
./start --docker     # Start container (migrations run automatically, port 5432)
./stop --docker      # Stop container
```

## Lifecycle Scripts

| Script  | Purpose |
|---------|---------|
| `setup` | Install PostgreSQL (native) or pull the postgres image (`--docker`) |
| `start` | Start the PostgreSQL service (native) or `hlvmp-db` container (`--docker`) |
| `stop`  | Stop the service/container (auto-detects Docker) |
| `build` | Run migrations (native) or build the `hlvmp-db` image (`--docker`) |
| `test`  | Verify connectivity and that migrations/schema are applied |

## Configuration

Configure via `.env` (see `.env.example`):

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=hlvmp
POSTGRES_PASSWORD=hlvmppass
POSTGRES_DB=hlvmp

# Legacy fallback used by ./build and ./test
#DATABASE_URL=postgresql://hlvmp:hlvmppass@localhost:5432/hlvmp
```

## Schema

Migrations are plain SQL files in `migrations/`, applied in order and tracked in
`migration_history`.

### jobs
- id, type, status, target_host_id, target_vm_id (nullable)
- payload (JSONB), result (JSONB), error (TEXT)
- claimed_by, claimed_at, started_at, finished_at
- attempts, max_attempts
- created_at, updated_at

### job_events
- id, job_id, level, message, metadata (JSONB), created_at

### resource_locks
- lock_key, job_id, worker_id, acquired_at, expires_at

Additional migrations add domain state, snapshots, VM logs, and RabbitMQ job
fields. See files in `migrations/`.

## Migration Strategy

- Plain SQL files, named `NNN_description.sql`, executed in order.
- Applied migrations recorded in `migration_history` (never re-applied).
- Never modify an existing migration — add a new one for schema changes.
- Native: `./build` applies migrations. Docker: the entrypoint applies them on
  container startup.

## Supported Platforms

**Native Installation:**
- Debian/Ubuntu (apt-get)
- RHEL/Fedora/Rocky/Alma (dnf)
- CentOS (yum)
- Arch Linux (pacman)
- openSUSE (zypper)

**Service Managers:** systemd, SysVinit, OpenRC

**Docker Mode:** Any Linux distribution with Docker Engine

## Relationship to Other Components

- **homelab-vm-provisioner-db-interface**: HTTP REST layer over this database.
  Start and migrate PostgreSQL before the interface starts.
- **homelab-vm-provisioner-api** / **homelab-vm-provisioner-worker**: talk to the
  db-interface, not directly to PostgreSQL.

## Common Gotchas

- **Connection Errors**: Ensure PostgreSQL is running and the database/user exist.
- **Migration Failures**: Check SQL syntax; migrations should be idempotent where
  possible.
- **Lock Contention**: Resource locks expire automatically, but crashed workers
  may leave stale locks (cleaned via the interface's lock cleanup endpoint).

## AI Agent Guidance

When modifying this subproject:
- Add migrations for schema changes (never modify existing migrations)
- Keep `build`/`start`/`stop`/`test` idempotent
- The repository/REST code lives in `homelab-vm-provisioner-db-interface`
- Update this file with new capabilities
