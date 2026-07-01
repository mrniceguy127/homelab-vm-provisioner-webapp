# Docker Mode: db-interface Microservice

This document describes Docker mode for the db-interface microservice. The image
is **node-only** and connects to an external PostgreSQL instance managed by the
`homelab-vm-provisioner-db` component.

## Architecture

In Docker mode:
- The microservice runs on port 3002 and is exposed to the host
- PostgreSQL is **not** part of this image — it runs in the `hlvmp-db` container
  (or natively) and is reached over the network via `POSTGRES_HOST`
- No migrations are run here (migrations belong to `homelab-vm-provisioner-db`)

## Quick Start

```bash
# 1. Start PostgreSQL first (separate component)
cd ../homelab-vm-provisioner-db
./build --docker && ./start --docker   # runs migrations on startup

# 2. Build and start the interface
cd ../homelab-vm-provisioner-db-interface
./build --docker
./start --docker

# Verify health
curl http://localhost:3002/health

# View logs
docker logs hlvmp-db-interface

# Stop
docker stop hlvmp-db-interface
```

## Image Details

- **Image name:** `hlvmp-db-interface:latest`
- **Base image:** `node:20-bookworm-slim`
- **Exposed port:** 3002
- **No volume** (stateless; all state lives in PostgreSQL)

## Environment Variables

Configure via `.env`:

```bash
# Microservice
DB_SERVICE_PORT=3002
DB_SERVICE_PASSWORD=changeme_db_secret

# PostgreSQL connection (points at hlvmp-db / native PostgreSQL)
# In Docker on Linux, use the bridge IP to reach the host-exposed database port.
POSTGRES_HOST=172.17.0.1
POSTGRES_PORT=5432
POSTGRES_USER=hlvmp
POSTGRES_PASSWORD=hlvmppass
POSTGRES_DB=hlvmp

# Legacy fallback
#DATABASE_URL=postgresql://hlvmp:hlvmppass@172.17.0.1:5432/hlvmp
```

## Container Lifecycle

```bash
./build --docker     # Build image
./start --docker     # Create/refresh and start container
docker stop hlvmp-db-interface
docker rm -f hlvmp-db-interface
```

The start script recreates the container when the image or configuration changes,
using a config-hash label to detect drift.
