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

---

# API Endpoint Reference

## Authentication

All endpoints except `/health` require authentication via `Authorization` header:

```bash
Authorization: Bearer <DB_SERVICE_PASSWORD>
```

## Endpoints

### `GET /health`

Health check endpoint (no auth required).

**Response 200:**
```json
{
  "ok": true,
  "database": "connected"
}
```

### `POST /jobs`

Enqueue a new job.

**Request:**
```json
{
  "type": "provision_vm",
  "targetHostId": "local",
  "targetVmId": "devbox",
  "payload": {
    "config": {...},
    "sshPublicKey": "...",
    "setupScript": "..."
  },
  "maxAttempts": 3
}
```

**Response 200:**
```json
{
  "id": "123",
  "type": "provision_vm",
  "status": "queued",
  "targetHostId": "local",
  "targetVmId": "devbox",
  "payload": {...},
  "attempts": 0,
  "maxAttempts": 3,
  "createdAt": "2026-06-23T10:00:00.000Z",
  "updatedAt": "2026-06-23T10:00:00.000Z"
}
```

### `GET /jobs`

List jobs with optional filtering.

**Query Parameters:**
- `status`: Filter by status (`queued`, `running`, `succeeded`, `failed`, `cancelled`)
- `targetHostId`: Filter by target host
- `targetVmId`: Filter by target VM
- `limit`: Max results (default: 100, max: 1000)
- `offset`: Pagination offset (default: 0)

**Response 200:**
```json
{
  "jobs": [
    {
      "id": "123",
      "type": "provision_vm",
      "status": "queued",
      "targetHostId": "local",
      "targetVmId": "devbox",
      "createdAt": "2026-06-23T10:00:00.000Z"
    }
  ],
  "total": 1
}
```

### `GET /jobs/:id`

Get job details.

**Response 200:**
```json
{
  "id": "123",
  "type": "provision_vm",
  "status": "running",
  "targetHostId": "local",
  "targetVmId": "devbox",
  "payload": {...},
  "result": null,
  "error": null,
  "claimedBy": "worker-host-12345",
  "claimedAt": "2026-06-23T10:00:05.000Z",
  "startedAt": "2026-06-23T10:00:06.000Z",
  "finishedAt": null,
  "attempts": 1,
  "maxAttempts": 3,
  "createdAt": "2026-06-23T10:00:00.000Z",
  "updatedAt": "2026-06-23T10:00:06.000Z"
}
```

### `GET /jobs/:id/events`

Get job event log.

**Response 200:**
```json
{
  "events": [
    {
      "id": "456",
      "jobId": "123",
      "level": "info",
      "message": "Job claimed by worker",
      "metadata": {"workerId": "worker-host-12345"},
      "createdAt": "2026-06-23T10:00:05.000Z"
    },
    {
      "id": "457",
      "jobId": "123",
      "level": "info",
      "message": "Starting VM provisioning",
      "metadata": null,
      "createdAt": "2026-06-23T10:00:06.000Z"
    }
  ]
}
```

### `POST /jobs/:id/events`

Append event to job log.

**Request:**
```json
{
  "level": "info",
  "message": "Provisioning completed",
  "metadata": {"duration_ms": 45000}
}
```

**Response 200:**
```json
{
  "id": "458",
  "jobId": "123",
  "level": "info",
  "message": "Provisioning completed",
  "metadata": {"duration_ms": 45000},
  "createdAt": "2026-06-23T10:00:51.000Z"
}
```

### `POST /jobs/:id/cancel`

Cancel a queued job.

**Response 200:**
```json
{
  "id": "123",
  "status": "cancelled",
  "updatedAt": "2026-06-23T10:01:00.000Z"
}
```

**Response 400:**
```json
{
  "error": "Job cannot be cancelled (status: running)"
}
```

### `POST /jobs/claim`

Claim next available job for host (worker use only).

**Request:**
```json
{
  "targetHostId": "local",
  "workerId": "worker-host-12345"
}
```

**Response 200:**
```json
{
  "id": "123",
  "type": "provision_vm",
  "targetHostId": "local",
  "targetVmId": "devbox",
  "payload": {...},
  "claimedBy": "worker-host-12345",
  "claimedAt": "2026-06-23T10:00:05.000Z"
}
```

**Response 204:**
No jobs available (empty body).

### `POST /jobs/:id/running`

Mark job as running (worker use only).

**Request:**
```json
{
  "workerId": "worker-host-12345"
}
```

**Response 200:**
```json
{
  "id": "123",
  "status": "running",
  "startedAt": "2026-06-23T10:00:06.000Z"
}
```

### `POST /jobs/:id/succeeded`

Mark job as succeeded (worker use only).

**Request:**
```json
{
  "result": {
    "vmName": "devbox",
    "ipAddress": "192.168.100.50"
  }
}
```

**Response 200:**
```json
{
  "id": "123",
  "status": "succeeded",
  "result": {...},
  "finishedAt": "2026-06-23T10:00:51.000Z"
}
```

### `POST /jobs/:id/failed`

Mark job as failed (worker use only).

**Request:**
```json
{
  "error": "VM name already exists",
  "retriable": false
}
```

**Response 200:**
```json
{
  "id": "123",
  "status": "failed",
  "error": "VM name already exists",
  "finishedAt": "2026-06-23T10:00:15.000Z"
}
```

### `POST /locks/acquire`

Acquire resource locks (worker use only).

**Request:**
```json
{
  "jobId": "123",
  "workerId": "worker-host-12345",
  "lockKeys": ["vm:devbox", "network:local"],
  "ttlMs": 300000
}
```

**Response 200:**
```json
{
  "acquired": true,
  "locks": [
    {
      "lockKey": "vm:devbox",
      "jobId": "123",
      "workerId": "worker-host-12345",
      "expiresAt": "2026-06-23T10:05:00.000Z"
    },
    {
      "lockKey": "network:local",
      "jobId": "123",
      "workerId": "worker-host-12345",
      "expiresAt": "2026-06-23T10:05:00.000Z"
    }
  ]
}
```

**Response 409:**
```json
{
  "acquired": false,
  "error": "Lock already held",
  "conflictingLocks": ["vm:devbox"]
}
```

### `POST /locks/release`

Release resource locks (worker use only).

**Request:**
```json
{
  "jobId": "123",
  "workerId": "worker-host-12345"
}
```

**Response 200:**
```json
{
  "released": 2
}
```

### `POST /locks/cleanup`

Cleanup expired locks (worker use only).

**Response 200:**
```json
{
  "cleaned": 3
}
```

## Error Responses

### 401 Unauthorized
Missing or invalid `Authorization` header.

```json
{
  "error": "Unauthorized"
}
```

### 404 Not Found
Job not found.

```json
{
  "error": "Job not found"
}
```

### 500 Internal Server Error
Database or server error.

```json
{
  "error": "Internal server error",
  "details": "..."
}
```

---

## License

MIT

