# PostgreSQL Database Integration

This document describes how to set up and use the PostgreSQL-backed async job queue microservice for the Homelab VM Provisioner.

## Overview

The database layer provides:
- Async job queue for long-running provisioning operations
- Event logging for job debugging and audit trails
- Resource locks to prevent concurrent operations on the same VM/host
- REST API microservice for database operations (port 3002)
- Native PostgreSQL for production deployments
- Docker mode for development convenience

## Architecture

The database is accessed through a dedicated microservice:

```
API (3001) → DB Microservice (3002) → PostgreSQL (5432)
```

The DB microservice:
- Manages PostgreSQL connections
- Validates SQL operations
- Exposes REST API for job operations
- Isolates database logic from the API service

## Quick Start

### 1. Install and Start PostgreSQL

**Native PostgreSQL (Recommended for Production):**

```bash
cd homelab-vm-provisioner-db
./setup                # Install PostgreSQL server and client + Express
./start                # Start PostgreSQL service
```

Create database and user:

```bash
sudo -u postgres psql -c "CREATE DATABASE hlvmp;"
sudo -u postgres psql -c "CREATE USER hlvmp WITH PASSWORD 'hlvmppass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE hlvmp TO hlvmp;"
```

**Docker Mode (Development):**

```bash
cd homelab-vm-provisioner-db
./setup --docker       # Install Docker, npm dependencies
./build --docker       # Build Docker image (PostgreSQL + microservice)
./start --docker       # Start container (migrations run automatically)
```

Docker mode runs PostgreSQL and the microservice in a single container. PostgreSQL port (5432) is internal only; only the microservice port (3002) is exposed.

### 2. Run Migrations

**Native Mode:**

```bash
cd homelab-vm-provisioner-db
npm run migrate
```

**Docker Mode:** Migrations run automatically when the container starts (no manual step needed).

### 3. Start Database Microservice

**Native Mode:**

```bash
cd homelab-vm-provisioner-db
npm start              # Microservice on port 3002
```

**Docker Mode:** Microservice starts automatically in the container (no manual step needed).

### 4. Configure API

Add `DB_SERVICE_URL` to your API `.env`:

```bash
cd homelab-vm-provisioner-api
cp .env.example .env   # If not already done
```

Edit `.env` and ensure this line is present:

```bash
DB_SERVICE_URL=http://localhost:3002
```

### 5. Start API

```bash
cd homelab-vm-provisioner-api
```bash
cd homelab-vm-provisioner-api
npm start
```

The API will connect to the database microservice on startup. If `DB_SERVICE_URL` is not set, the API will still start but job queue endpoints will return 503.

## Architecture

### Components

```
API Server (Node.js) → DB Microservice (Express) → PostgreSQL
     ↓                         ↓                        ↓
  REST API             Repository API          Durable Storage
```

- **API Server**: Enqueues jobs, queries job status, provides REST endpoints
- **DB Microservice**: Manages PostgreSQL connections, validates SQL, exposes job repository API
- **PostgreSQL**: Durable storage for jobs, events, locks
- **Worker Process**: (Not yet implemented) Claims and executes jobs

### Authentication

The database microservice requires authentication for all endpoints except `/health`. Authentication uses a shared secret password configured via the `DB_SERVICE_PASSWORD` environment variable.

**API sends:**
```
Authorization: Bearer <DB_SERVICE_PASSWORD>
```

**Microservice validates:**
- Checks `Authorization` header on all requests (except `/health`)
- Returns `401 Unauthorized` if missing or invalid
- Supports both `Bearer <password>` and `<password>` formats

**Configuration:**
- Set `DB_SERVICE_PASSWORD` in both API and database microservice `.env` files
- Use a strong password in production (default `changeme_db_secret` is for development only)
- Change the password regularly
- Use TLS/HTTPS for production to protect the password in transit

### Database Schema

#### jobs Table

Tracks async provisioning jobs:

```sql
id               BIGSERIAL PRIMARY KEY
type             VARCHAR(100)           -- Job type (e.g., 'provision_vm')
status           VARCHAR(50)            -- 'queued', 'running', 'succeeded', 'failed', 'cancelled'
target_host_id   VARCHAR(255)           -- Host where job runs
target_vm_id     VARCHAR(255) NULL      -- Target VM (if applicable)
payload          JSONB                  -- Job input parameters
result           JSONB NULL             -- Job output data
error            TEXT NULL              -- Error message (if failed)
claimed_by       VARCHAR(255) NULL      -- Worker ID
claimed_at       TIMESTAMPTZ NULL       -- When claimed
started_at       TIMESTAMPTZ NULL       -- When started
finished_at      TIMESTAMPTZ NULL       -- When completed
attempts         INTEGER                -- Execution attempts
max_attempts     INTEGER                -- Max retry attempts
created_at       TIMESTAMPTZ
updated_at       TIMESTAMPTZ
```

#### job_events Table

Event log per job:

```sql
id          BIGSERIAL PRIMARY KEY
job_id      BIGINT REFERENCES jobs(id)
level       VARCHAR(50)             -- 'debug', 'info', 'warning', 'error'
message     TEXT                    -- Event message
metadata    JSONB NULL              -- Additional context
created_at  TIMESTAMPTZ
```

#### resource_locks Table

Prevents concurrent operations:

```sql
lock_key    VARCHAR(255) PRIMARY KEY  -- Resource identifier
job_id      BIGINT REFERENCES jobs(id)
worker_id   VARCHAR(255)
acquired_at TIMESTAMPTZ
expires_at  TIMESTAMPTZ
```

## Database Microservice Endpoints (Internal API)

**Note:** These endpoints are exposed by the database microservice (port 3002) and are **not available as public API endpoints**. The main API (port 3001) uses these internally via the database client. External users do not have direct access to job operations.

### List Jobs

```bash
GET /jobs?status=queued&targetHostId=local&limit=50
Authorization: Bearer <DB_SERVICE_PASSWORD>
```

Response:
```json
{
  "jobs": [
    {
      "id": 1,
      "type": "provision_vm",
      "status": "queued",
      "targetHostId": "local",
      "targetVmId": "test-vm",
      "payload": { "vmName": "test-vm", "config": {...} },
      "result": null,
      "error": null,
      "attempts": 0,
      "maxAttempts": 3,
      "createdAt": "2026-06-17T12:00:00Z",
      "updatedAt": "2026-06-17T12:00:00Z"
    }
  ]
}
```

### Enqueue Job

```bash
POST /jobs
Authorization: Bearer <DB_SERVICE_PASSWORD>
Content-Type: application/json

{
  "type": "provision_vm",
  "targetHostId": "local",
  "targetVmId": "test-vm",
  "payload": {
    "vmName": "test-vm",
    "config": {...}
  },
  "maxAttempts": 3
}
```

Response:
```json
{
  "job": {
    "id": 1,
    "type": "provision_vm",
    "status": "queued",
    ...
  }
}
```

### Get Job

```bash
GET /jobs/1
Authorization: Bearer <DB_SERVICE_PASSWORD>
```

Response:
```json
{
  "job": {
    "id": 1,
    "type": "provision_vm",
    "status": "running",
    ...
  }
}
```

### Get Job Events

```bash
GET /jobs/1/events
Authorization: Bearer <DB_SERVICE_PASSWORD>
```

Response:
```json
{
  "events": [
    {
      "id": 1,
      "jobId": 1,
      "level": "info",
      "message": "Starting VM provisioning",
      "metadata": null,
      "createdAt": "2026-06-17T12:00:01Z"
    },
    {
      "id": 2,
      "jobId": 1,
      "level": "info",
      "message": "Network configured",
      "metadata": { "ip": "10.80.0.5" },
      "createdAt": "2026-06-17T12:00:02Z"
    }
  ]
}
```

### Cancel Job

```bash
POST /jobs/1/cancel
Authorization: Bearer <DB_SERVICE_PASSWORD>
```

Response:
```json
{
  "job": {
    "id": 1,
    "status": "cancelled",
    ...
  }
}
```

## Worker Implementation (Future)

Workers will:
1. Claim jobs using `FOR UPDATE SKIP LOCKED` (race-free)
2. Execute provisioning operations
3. Update job status and append events
4. Release resource locks on completion

Example worker pseudocode:

```javascript
async function worker(workerId) {
  const repo = await createRepository(process.env.DATABASE_URL);
  
  while (true) {
    // Claim next job for this host
    const job = await repo.claimNextJobForHost('local', workerId);
    
    if (!job) {
      await sleep(5000);
      continue;
    }
    
    try {
      // Mark as running
      await repo.markJobRunning(job.id, workerId);
      await repo.appendJobEvent(job.id, 'info', 'Starting job');
      
      // Acquire resource lock
      const locked = await repo.acquireResourceLocks(
        job.id,
        workerId,
        [`vm:${job.targetVmId}`],
        300000  // 5 minute TTL
      );
      
      if (!locked) {
        await repo.markJobFailed(job.id, 'Resource locked', true);
        continue;
      }
      
      // Execute job
      const result = await executeJob(job);
      
      // Mark as succeeded
      await repo.markJobSucceeded(job.id, result);
      await repo.appendJobEvent(job.id, 'info', 'Job completed');
      
      // Release locks
      await repo.releaseResourceLocks(job.id, workerId);
    } catch (error) {
      await repo.markJobFailed(job.id, error.message, true);
      await repo.appendJobEvent(job.id, 'error', error.message);
      await repo.releaseResourceLocks(job.id, workerId);
    }
  }
}
```

## Configuration

### Environment Variables

#### API (.env)

```bash
# Required for job queue features
DB_SERVICE_URL=http://localhost:3002

# Database microservice authentication (shared secret)
DB_SERVICE_PASSWORD=changeme_db_secret

# Optional
API_PORT=3001
```

#### Database Microservice (.env)

```bash
# Microservice port
DB_SERVICE_PORT=3002

# Database microservice authentication (shared secret)
# Must match the password configured in the API
DB_SERVICE_PASSWORD=changeme_db_secret

# PostgreSQL connection (used by microservice)
DATABASE_URL=postgresql://hlvmp:hlvmppass@localhost:5432/hlvmp

# Container settings (for Docker mode only)
POSTGRES_PORT=5432
POSTGRES_USER=hlvmp
POSTGRES_PASSWORD=hlvmppass
POSTGRES_DB=hlvmp
```

## Migrations

Migrations are plain SQL files in `homelab-vm-provisioner-db/migrations/`:

```
001_initial_schema.sql
002_add_indexes.sql
...
```

Applied migrations are tracked in `migration_history` table.

### Running Migrations

```bash
cd homelab-vm-provisioner-db
npm run migrate
```

### Creating Migrations

1. Create a new SQL file with sequential numbering:
   ```bash
   touch migrations/002_add_priority_column.sql
   ```

2. Add SQL statements:
   ```sql
   ALTER TABLE jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 0;
   CREATE INDEX idx_jobs_priority ON jobs(priority, created_at);
   ```

3. Run migrations:
   ```bash
   npm run migrate
   ```

## Development Workflow

### Native PostgreSQL (Default)

```bash
# Terminal 1: Start Postgres and DB microservice
cd homelab-vm-provisioner-db
./start              # Start native service
npm start            # Start microservice (port 3002)

# Terminal 2: Start API
cd homelab-vm-provisioner-api
npm start

# Terminal 3: Test microservice health and API
curl http://localhost:3002/health                    # DB microservice health
curl http://localhost:3001/api/vms                   # API endpoint
```

### Docker Mode (Development)

```bash
# Terminal 1: Start container (PostgreSQL + microservice)
cd homelab-vm-provisioner-db
./start --docker     # Port 3002 exposed

# Terminal 2: Start API
cd homelab-vm-provisioner-api
npm start

# Terminal 3: Test microservice health and API
curl http://localhost:3002/health                    # DB microservice health
curl http://localhost:3001/api/vms                   # API endpoint
```

# Terminal 4: Test job endpoints
curl http://localhost:3001/api/jobs
```

### Testing

Currently no automated tests for the database layer. Manual verification:

**Native:**
```bash
# Start Postgres natively
cd homelab-vm-provisioner-db
./start
npm run migrate
npm start              # Start microservice

# Verify connection via microservice
curl http://localhost:3002/health

# Should return: {"status":"ok"}
```

**Docker:**
```bash
# Start container (PostgreSQL + microservice)
cd homelab-vm-provisioner-db
./start --docker       # Migrations run automatically

# Verify container is running
docker ps | grep hlvmp-db

# Check health
curl http://localhost:3002/health
```

### Resetting Database

**Native:**
```bash
# Drop and recreate database
sudo -u postgres psql -c "DROP DATABASE hlvmp;"
sudo -u postgres psql -c "CREATE DATABASE hlvmp;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE hlvmp TO hlvmp;"

# Re-run migrations
cd homelab-vm-provisioner-db
npm run migrate
```

**Docker:**
```bash
cd homelab-vm-provisioner-db
docker stop hlvmp-db
docker rm hlvmp-db
docker volume rm hlvmp-postgres-data
./start --docker       # Migrations run automatically
```
```

## Production Considerations

**Not production-ready yet.** Before deploying:

1. **Security**
   - ✓ Basic authentication implemented (shared secret between API and DB microservice)
   - Change default passwords (DB_SERVICE_PASSWORD and PostgreSQL credentials)
   - Use TLS for database microservice connections
   - Restrict database network access
   - Add per-user authentication/authorization (currently single shared secret)

2. **Reliability**
   - Implement job timeout detection
   - Add dead letter queue for failed jobs
   - Implement worker health checks
   - Add job priority support

3. **Monitoring**
   - Add metrics for job queue depth
   - Monitor job execution times
   - Alert on failed jobs
   - Track lock contention

4. **Scaling**
   - Use managed Postgres (RDS, Cloud SQL, etc.)
   - Implement connection pooling (PgBouncer)
   - Add read replicas for reporting queries
   - Partition old jobs for performance

## Troubleshooting

### Microservice connection fails

```bash
# Check if microservice is running
# Native mode:
ps aux | grep "node src/server.js"

# Docker mode:
docker ps | grep hlvmp-db
docker logs hlvmp-db

# Test health endpoint
curl http://localhost:3002/health
```

### Database connection fails (Native mode)

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Test PostgreSQL connection
psql postgresql://hlvmp:hlvmppass@localhost:5432/hlvmp -c 'SELECT 1'
```

### Migrations fail

```bash
# Native mode - check migration_history
psql $DATABASE_URL -c 'SELECT * FROM migration_history'

# Docker mode - check logs
docker logs hlvmp-db

# Manually rollback if needed (no automatic rollback)
# Fix migration SQL, then re-run
npm run migrate          # Native mode
./start --docker         # Docker mode (migrations run on startup)
```

### API can't connect to database

```bash
# Verify DATABASE_URL in API .env
cd homelab-vm-provisioner-api
cat .env | grep DATABASE_URL

# Check API logs for connection errors
npm start
```

## Future Enhancements

- Worker implementation for job execution
- Job priority support
- Scheduled/cron jobs
- Job dependencies (job A must complete before job B)
- Bulk job operations
- Job result pagination
- Webhook notifications on job completion
- Admin UI for job management
