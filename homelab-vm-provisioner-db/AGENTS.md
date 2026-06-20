# Database Layer (homelab-vm-provisioner-db)

PostgreSQL-backed async job queue and event log for the homelab VM provisioner.

## Overview

This subproject provides:
- PostgreSQL schema for jobs, events, and resource locks
- Migration tooling
- Repository/service layer for job operations
- Native PostgreSQL setup for production
- Docker mode for development convenience

## Quick Commands

```bash
# Native PostgreSQL (default, recommended)
./setup              # Install PostgreSQL server and client + Express
./start              # Start PostgreSQL service
npm run migrate      # Run migrations
npm start            # Start microservice (port 3002)

# Docker mode (development)
./setup --docker     # Install npm dependencies
./build --docker     # Build Docker image (PostgreSQL + microservice)
./start --docker     # Start container (migrations run automatically, port 3002)
```

## Tech Stack

- **Database**: PostgreSQL 17
- **Driver**: node-postgres (pg)
- **Migrations**: Plain SQL, version-tracked
- **Runtime**: Node.js ESM

## Supported Platforms

**Native Installation:**
- Debian/Ubuntu (apt-get)
- RHEL/Fedora/Rocky/Alma (dnf)
- CentOS (yum)
- Arch Linux (pacman)
- openSUSE (zypper)

**Service Managers:**
- systemd (most modern Linux)
- SysVinit
- OpenRC (Alpine, Gentoo)

**Docker Mode:**
- Any Linux distribution with Docker Engine

## Schema

### jobs
- id, type, status, target_host_id, target_vm_id (nullable)
- payload (JSONB), result (JSONB), error (TEXT)
- claimed_by, claimed_at, started_at, finished_at
- attempts, max_attempts
- created_at, updated_at

### job_events
- id, job_id, level, message, metadata (JSONB)
- created_at

### resource_locks
- lock_key, job_id, worker_id
- acquired_at, expires_at

### migration_history
- version, applied_at

## Repository API

All database operations go through `src/repository.js`:

```js
import { createRepository } from './repository.js';

const repo = await createRepository(process.env.DATABASE_URL);

// Enqueue a job
const job = await repo.enqueueJob('provision_vm', 'local', { vmName: 'test' });

// Claim next job for this host
const claimed = await repo.claimNextJobForHost('local', 'worker-1');

// Mark job running
await repo.markJobRunning(claimed.id, 'worker-1');

// Append event
await repo.appendJobEvent(claimed.id, 'info', 'Starting provisioning');

// Mark job succeeded
await repo.markJobSucceeded(claimed.id, { vmId: '123' });

// Get job details
const job = await repo.getJob(claimed.id);

// List events
const events = await repo.listJobEvents(claimed.id);
```

## Job Claiming Strategy

Uses `FOR UPDATE SKIP LOCKED` to safely claim jobs:

```sql
SELECT * FROM jobs
WHERE status = 'queued' AND target_host_id = $1
ORDER BY created_at
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

Multiple workers can run concurrently without race conditions.

## Migration Strategy

Migrations are plain SQL files in `migrations/`, named:

```
001_initial_schema.sql
002_add_indexes.sql
...
```

Executed in order. Applied migrations tracked in `migration_history` table.

Run: `npm run migrate`

## Environment Variables

```bash
# Required
POSTGRES_HOST=host
POSTGRES_PORT=5432
POSTGRES_USER=user
POSTGRES_PASSWORD=pass
POSTGRES_DB=dbname
DB_SERVICE_PASSWORD=changeme_db_secret  # Auth token for microservice endpoints

# Optional
DB_SERVICE_PORT=3002  # Microservice port

# Optional (for Docker mode)
POSTGRES_PORT=5432
POSTGRES_USER=hlvmp
POSTGRES_PASSWORD=hlvmppass
POSTGRES_DB=hlvmp
```

## Native Mode (Default)

Production-ready native PostgreSQL installation:

```bash
./setup              # Install PostgreSQL
./start              # Start service
npm run migrate      # Apply migrations
```

After setup, create database and user:

```bash
sudo -u postgres psql -c "CREATE DATABASE hlvmp;"
sudo -u postgres psql -c "CREATE USER hlvmp WITH PASSWORD 'hlvmppass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE hlvmp TO hlvmp;"
```

Set PostgreSQL connection values in `.env`:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=hlvmp
POSTGRES_PASSWORD=hlvmppass
POSTGRES_DB=hlvmp
```

## Docker Mode

Development convenience mode that runs PostgreSQL and the microservice in a single container:

```bash
./setup --docker     # Install dependencies
./build --docker     # Build hlvmp-db image
./start --docker     # Start container
```

The container includes:
- PostgreSQL 17 (internal port 5432, not exposed)
- Database microservice (port 3002, exposed to host)
- Named volume `hlvmp-postgres-data`
- Automatic migrations on startup
- Credentials from .env

Only the microservice port (3002) is accessible from the host. PostgreSQL is internal to the container.

## Testing

Currently no automated tests. Manual verification:

```bash
# Native mode
./start
npm run migrate
npm start
curl http://localhost:3002/health

# Docker mode
./start --docker
curl http://localhost:3002/health
```

## Common Gotchas

- **Connection Errors**: Ensure DATABASE_URL is set and Postgres is running
- **Migration Failures**: Check migration SQL syntax, ensure migrations are idempotent where possible
- **Lock Contention**: Resource locks expire automatically, but manual cleanup may be needed if workers crash

## AI Agent Guidance

When modifying this subproject:
- Keep the repository API stable
- Add migrations for schema changes (never modify existing migrations)
- Use parameterized queries, never string concatenation
- Follow existing patterns for error handling
- Update this file with new capabilities
