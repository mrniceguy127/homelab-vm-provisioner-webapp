# Database (homelab-vm-provisioner-db)

PostgreSQL infrastructure component. Owns the database engine and SQL schema
(migrations) for job metadata, event logs, resource locks, and VM records.

This component is **PostgreSQL only**. The HTTP REST interface lives in
`homelab-vm-provisioner-db-interface`. Job delivery is handled by RabbitMQ
(`homelab-vm-provisioner-job-queue`).

## Overview

This subproject provides:
- PostgreSQL installation (native) and a Docker image (`hlvmp-db`)
- SQL migrations (schema provisioning) tracked in `migration_history`
- Lifecycle scripts mirroring other infrastructure components:
  `setup`, `start`, `stop`, `build`, `test`

It does **not** contain application/repository code or an HTTP server.

## Quick Commands

```bash
# Native (default)
./setup              # Install PostgreSQL server + client
./start              # Start PostgreSQL service
./build              # Run migrations
./test               # Verify connectivity + schema
./stop               # Stop PostgreSQL service

# Docker mode
./setup --docker     # Pull postgres image
./build --docker     # Build hlvmp-db image (postgres + migrations)
./start --docker     # Start container (migrations run on startup)
./stop --docker      # Stop container
```

## Tech Stack

- **Database**: PostgreSQL 17
- **Migrations**: Plain SQL, version-tracked in `migration_history`
- **Scripts**: Bash (no npm dependencies)

## Environment Variables

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=hlvmp
POSTGRES_PASSWORD=hlvmppass
POSTGRES_DB=hlvmp
# Legacy fallback used by build/test
#DATABASE_URL=postgresql://hlvmp:hlvmppass@localhost:5432/hlvmp
```

## Docker

- **Image**: `hlvmp-db:latest` (base `postgres:17`)
- **Container**: `hlvmp-db`
- **Volume**: `hlvmp-postgres-data`
- **Exposes**: 5432
- Migrations are baked into the image and applied by the entrypoint on startup.

## Migration Strategy

- Plain SQL files in `migrations/`, named `NNN_description.sql`, applied in order.
- Applied migrations recorded in `migration_history`; never re-applied.
- Never modify an existing migration — add a new file for schema changes.

## Relationship to Other Components

- **homelab-vm-provisioner-db-interface**: REST layer over this database. Must be
  migrated and running before the interface serves traffic.
- **homelab-vm-provisioner-api** / **homelab-vm-provisioner-worker**: use the
  db-interface over HTTP, not PostgreSQL directly.

## AI Agent Guidance

When modifying this subproject:
- Add migrations for schema changes (never modify existing migrations)
- Keep lifecycle scripts idempotent and safe to re-run
- Repository/REST code belongs in `homelab-vm-provisioner-db-interface`
- Update this file with new capabilities
