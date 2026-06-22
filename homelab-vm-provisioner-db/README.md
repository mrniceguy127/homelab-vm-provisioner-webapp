# Homelab VM Provisioner Database

PostgreSQL database microservice for async provisioner jobs.

## Quick Start

```bash
# Native PostgreSQL (default, recommended for production)
./setup              # Install PostgreSQL server and client + Express
./start              # Start PostgreSQL service
npm run migrate      # Run migrations
npm start            # Start database microservice (port 3002)

# Docker mode (for development)
./setup --docker     # Install npm dependencies
./build --docker     # Build Docker image (PostgreSQL + microservice)
./start --docker     # Start container (migrations run automatically, port 3002)

# Stop
# Native: Ctrl+C (microservice), sudo systemctl stop postgresql
# Docker: docker stop hlvmp-db
```

## Architecture

This is a microservice that:
- Manages PostgreSQL connections and queries
- Validates SQL operations
- Exposes REST API on port 3002 (configurable)
- Requires authentication via `Authorization` header (shared secret)
- Used by the API service (port 3001) for job queue operations

In Docker mode, PostgreSQL and the microservice run in a single container with only the microservice port exposed.

**Authentication:**
All endpoints except `/health` require an `Authorization` header with the configured password (`DB_SERVICE_PASSWORD`). The API must send this password with every request.

## Native Development (Default)

Native PostgreSQL is the default and recommended approach:

```bash
# Install PostgreSQL
./setup

# Start service
./start

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE hlvmp;"
sudo -u postgres psql -c "CREATE USER hlvmp WITH PASSWORD 'hlvmppass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE hlvmp TO hlvmp;"

# Set database connection values in .env
echo "POSTGRES_HOST=localhost" > .env
echo "POSTGRES_PORT=5432" >> .env
echo "POSTGRES_USER=hlvmp" >> .env
echo "POSTGRES_PASSWORD=hlvmppass" >> .env
echo "POSTGRES_DB=hlvmp" >> .env
echo "DB_SERVICE_PORT=3002" >> .env
echo "DB_SERVICE_PASSWORD=changeme_db_secret" >> .env

# Run migrations
npm run migrate

# Start microservice
npm start
```

## Docker Mode (Development)

Docker mode runs PostgreSQL and the microservice in a single container:

```bash
# Build and start container
./setup --docker
./build --docker     # Build hlvmp-db image
./start --docker     # Start container (migrations run automatically)

# Check health
curl http://localhost:3002/health

# View logs
docker logs hlvmp-db

# Stop
docker stop hlvmp-db
```

In Docker mode:
- PostgreSQL runs on port 5432 **inside the container only** (not exposed)
- Microservice runs on port 3002 and is exposed to the host
- Migrations run automatically when the container starts
- Both services are managed by a single container

## API Endpoints

The microservice exposes these REST endpoints:

**Public (no auth required):**
- `GET /health` - Health check

**Authenticated (require Authorization header):**
- `POST /jobs` - Enqueue a job
- `GET /jobs` - List jobs (with optional filters)
- `GET /jobs/:id` - Get job details
- `GET /jobs/:id/events` - Get job events
- `POST /jobs/:id/events` - Append job event
- `POST /jobs/:id/cancel` - Cancel a queued job
- `POST /jobs/claim` - Claim next job for host
- `POST /jobs/:id/running` - Mark job as running
- `POST /jobs/:id/succeeded` - Mark job as succeeded
- `POST /jobs/:id/failed` - Mark job as failed
- `POST /locks/acquire` - Acquire resource locks
- `POST /locks/release` - Release resource locks
- `POST /locks/cleanup` - Cleanup expired locks

**Authentication:**
```bash
# All authenticated endpoints require:
Authorization: Bearer <DB_SERVICE_PASSWORD>

# Example:
curl -H "Authorization: Bearer changeme_db_secret" http://localhost:3002/jobs
```

## Architecture

### Tables

- **jobs**: Async provisioning jobs with status tracking
- **job_events**: Event log per job for debugging and audit
- **resource_locks**: Per-resource locks to prevent concurrent operations

### Job Lifecycle

1. **queued** → Job created, waiting for worker
2. **running** → Claimed by worker, in progress
3. **succeeded** | **failed** | **cancelled** → Terminal states

### Job Claiming

Workers use `FOR UPDATE SKIP LOCKED` to safely claim jobs without race conditions.

## Configuration

Configure via `.env`:

```bash
# PostgreSQL connection
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=hlvmp
POSTGRES_PASSWORD=hlvmppass
POSTGRES_DB=hlvmp

# Legacy fallback
#DATABASE_URL=postgresql://hlvmp:hlvmppass@localhost:5432/hlvmp

# Container settings (for Docker mode only)
# Keep POSTGRES_HOST=localhost when the container includes PostgreSQL.
```

## Supported Distributions

Native PostgreSQL installation supports:
- Debian/Ubuntu (apt-get)
- RHEL/Fedora/Rocky/Alma (dnf)
- CentOS (yum)
- Arch Linux (pacman)
- openSUSE (zypper)

Service managers supported:
- systemd (most modern Linux)
- SysVinit
- OpenRC (Alpine, Gentoo)

## Migration

Migrations are plain SQL files in `migrations/` directory, executed in alphanumeric order.

Run migrations:

```bash
npm run migrate
```

## Repository API

See `src/repository.js` for the full API:

- `enqueueJob(type, targetHostId, payload, options)`
- `getJob(jobId)`
- `listJobEvents(jobId)`
- `appendJobEvent(jobId, level, message, metadata)`
- `claimNextJobForHost(targetHostId, workerId)`
- `markJobRunning(jobId, workerId)`
- `markJobSucceeded(jobId, result)`
- `markJobFailed(jobId, error, retriable)`
- `cancelQueuedJob(jobId)`
- `acquireResourceLocks(jobId, workerId, lockKeys, ttlMs)`
- `releaseResourceLocks(jobId, workerId)`

## License

MIT
