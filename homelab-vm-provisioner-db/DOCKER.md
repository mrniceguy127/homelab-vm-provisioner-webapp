# Docker Mode: PostgreSQL Database

This document describes Docker mode for the PostgreSQL database component. The
image contains **PostgreSQL only** (plus baked-in migrations). The HTTP REST
interface runs separately in `homelab-vm-provisioner-db-interface`.

## Architecture

In Docker mode:
- PostgreSQL 17 runs and is exposed to the host on `POSTGRES_PORT` (default 5432)
- Migrations run automatically when the container starts
- Data persists in the named volume `hlvmp-postgres-data`

## Quick Start

```bash
cd homelab-vm-provisioner-db

# Build image (postgres + migrations)
./build --docker

# Start container
./start --docker

# Verify connectivity + schema
POSTGRES_HOST=localhost ./test

# Connect directly
psql postgresql://hlvmp:hlvmppass@localhost:5432/hlvmp

# View logs
docker logs hlvmp-db

# Stop
./stop --docker
```

## Image Details

- **Image name:** `hlvmp-db:latest`
- **Base image:** `postgres:17`
- **Additional components:** migrations + custom entrypoint (applies migrations)
- **Exposed port:** 5432
- **Volume:** `hlvmp-postgres-data`

## Environment Variables

Configure via `.env`:

```bash
# Host port mapped to the container's 5432
POSTGRES_PORT=5432

# Database credentials (used to initialize the database on first run)
POSTGRES_USER=hlvmp
POSTGRES_PASSWORD=hlvmppass
POSTGRES_DB=hlvmp
```

## Connecting the db-interface

The db-interface container connects to this database over the network. On Linux
Docker, point it at the host bridge IP:

```bash
# In homelab-vm-provisioner-db-interface/.env
POSTGRES_HOST=172.17.0.1
POSTGRES_PORT=5432
```

## Container Lifecycle

```bash
./build --docker     # Build image
./start --docker     # Create/refresh and start container (migrations applied)
./stop --docker      # Stop container
docker rm -f hlvmp-db
```

The start script recreates the container when the image or configuration changes,
using a config-hash label to detect drift.
