# Database Interface (homelab-vm-provisioner-db-interface)

HTTP interface microservice for the provisioner's PostgreSQL store. It exposes a
REST API (default port 3002) for job metadata, event logs, resource locks, VM
definitions, runtime state, snapshots, and logs.

Job **delivery** is handled by RabbitMQ ([homelab-vm-provisioner-job-queue](../homelab-vm-provisioner-job-queue));
the durable data itself lives in PostgreSQL, which is managed by the separate
[homelab-vm-provisioner-db](../homelab-vm-provisioner-db) component. This service
is the HTTP layer in front of that database and does **not** install, start, or
migrate PostgreSQL.

## Quick Start

```bash
# Native (default)
./setup              # Install Node.js + npm dependencies
./start              # Start the microservice (port 3002)

# Docker mode
./setup --docker     # Install Node.js on host (dependencies baked into image)
./build --docker     # Build hlvmp-db-interface image (node only)
./start --docker     # Start the container (connects to external PostgreSQL)
```

This service requires a running PostgreSQL instance and applied migrations. Start
and migrate PostgreSQL first:

```bash
cd ../homelab-vm-provisioner-db
./setup && ./start && ./build   # ./build runs migrations
```

## Architecture

This is a microservice that:
- Connects to PostgreSQL via `POSTGRES_*` (or `DATABASE_URL`)
- Exposes a REST API on port 3002 (configurable via `DB_SERVICE_PORT`)
- Requires authentication via the `Authorization` header (shared secret)
- Serves job metadata, event logs, resource locks, and VM records
- Is used by the API (port 3001) and the worker daemon over HTTP
- Is **not** the job delivery queue — RabbitMQ delivers jobs to workers

**Authentication:** All endpoints except `/health` require an `Authorization`
header with `DB_SERVICE_PASSWORD`.

## Configuration

Configure via `.env` (see `.env.example`):

```bash
# Microservice
DB_SERVICE_PORT=3002
DB_SERVICE_PASSWORD=changeme_db_secret

# PostgreSQL connection (points at homelab-vm-provisioner-db)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=hlvmp
POSTGRES_PASSWORD=hlvmppass
POSTGRES_DB=hlvmp

# Legacy fallback
#DATABASE_URL=postgresql://hlvmp:hlvmppass@localhost:5432/hlvmp
```

## Repository API

All database operations go through `src/repository.js`:

```js
import { createRepository } from './repository.js';

const repo = await createRepository(process.env.DATABASE_URL);
const job = await repo.enqueueJob('provision_vm', 'local', { vmName: 'test' });
const claimed = await repo.claimNextJobForHost('local', 'worker-1');
await repo.markJobRunning(claimed.id, 'worker-1');
await repo.appendJobEvent(claimed.id, 'info', 'Starting provisioning');
await repo.markJobSucceeded(claimed.id, { vmId: '123' });
```

## REST Endpoints

**Public (no auth):**
- `GET /health` — Health check

**Authenticated (`Authorization: Bearer <DB_SERVICE_PASSWORD>`):**
- Jobs: `POST /jobs`, `GET /jobs`, `GET /jobs/:id`, `POST /jobs/claim`,
  `POST /jobs/:id/{running,succeeded,failed}`, `PATCH /jobs/:id/status`,
  `POST /jobs/:id/cancel`
- Job events: `GET/POST/DELETE /jobs/:id/events`
- Locks: `POST /locks/{acquire,release}`, `POST /locks/cleanup`
- Users: `GET/POST /users`
- Network groups: `GET/POST /network-groups`, `DELETE /network-groups/:id`
- VM definitions: `GET/POST /vm-definitions`, `POST /vm-definition-jobs`,
  and lookups/deletes by name or id
- VM runtime state: `GET/POST/DELETE /vm-runtime-state/:vmName`
- VM snapshots: `GET/POST/DELETE /vm-snapshots/:vmName/:snapshotId`
- VM logs: `GET/POST/DELETE /vm-logs/:vmName`

## Testing

```bash
npm test      # node --test test/*.test.js
```

## Common Gotchas

- **Connection errors**: Ensure PostgreSQL is running and migrations were applied
  (run `../homelab-vm-provisioner-db/build`).
- **401 responses**: Provide the `Authorization` header with `DB_SERVICE_PASSWORD`.
- **Schema changes**: Add migrations in `../homelab-vm-provisioner-db/migrations`,
  not here.

## AI Agent Guidance

When modifying this subproject:
- Keep the repository API stable
- Use parameterized queries, never string concatenation
- Schema/migrations live in `homelab-vm-provisioner-db`, not here
- Follow existing patterns for error handling
- Update this file with new capabilities
