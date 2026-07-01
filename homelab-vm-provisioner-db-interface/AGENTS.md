# Database Interface (homelab-vm-provisioner-db-interface)

HTTP interface microservice in front of the provisioner's PostgreSQL store.
Serves job metadata, event logs, resource locks, and VM records over REST.
PostgreSQL itself (install, service lifecycle, migrations) is owned by the
separate `homelab-vm-provisioner-db` component.

## Overview

This subproject provides:
- Express REST API on port 3002 (configurable)
- Repository/service layer (`src/repository.js`) over `node-postgres`
- Shared-secret authentication for all endpoints except `/health`
- Native and Docker (node-only image) run modes

It does **not** install or migrate PostgreSQL. It connects to an external
PostgreSQL instance via `POSTGRES_*` or `DATABASE_URL`.

## Quick Commands

```bash
# Native (default)
./setup              # Install Node.js + npm dependencies
./start              # Start microservice (node src/server.js, port 3002)

# Docker mode (node-only image)
./setup --docker     # Install Node.js on host
./build --docker     # Build hlvmp-db-interface image
./start --docker     # Start container (connects to external PostgreSQL)

npm test             # node --test test/*.test.js
```

## Tech Stack

- **Runtime**: Node.js ESM
- **Framework**: Express 4
- **Driver**: node-postgres (pg)
- **Tests**: node:test

## Environment Variables

```bash
# Required
DB_SERVICE_PASSWORD=changeme_db_secret   # Auth token for all endpoints except /health
POSTGRES_HOST=host
POSTGRES_PORT=5432
POSTGRES_USER=user
POSTGRES_PASSWORD=pass
POSTGRES_DB=dbname

# Optional
DB_SERVICE_PORT=3002                     # Microservice port
DATABASE_URL=postgresql://...            # Legacy fallback (overrides POSTGRES_* when set and no POSTGRES_* provided)
```

## Docker

- **Image**: `hlvmp-db-interface:latest` (base `node:20-bookworm-slim`)
- **Container**: `hlvmp-db-interface`
- **Exposes**: 3002
- Connects to PostgreSQL over the network (`POSTGRES_HOST`), typically the
  `hlvmp-db` container reached at `172.17.0.1:5432` on Linux Docker.

## Relationship to Other Components

- **homelab-vm-provisioner-db**: Owns PostgreSQL + migrations. Must be running
  and migrated before this service starts.
- **homelab-vm-provisioner-api** / **homelab-vm-provisioner-worker**: HTTP
  clients of this service via `DB_SERVICE_HOST`/`DB_SERVICE_PORT` and the
  `DB_SERVICE_PASSWORD` shared secret.

## AI Agent Guidance

When modifying this subproject:
- Keep the repository API and REST contract stable
- Use parameterized queries, never string concatenation
- Add schema changes as migrations in `homelab-vm-provisioner-db/migrations`
- Follow existing patterns for error handling
- Update this file with new capabilities
