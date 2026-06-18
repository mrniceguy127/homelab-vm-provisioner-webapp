# Docker Mode: Database Microservice

This document describes the Docker mode for the database microservice, which can run PostgreSQL and/or the Node.js microservice in a single container.

## Architecture

In Docker mode:
- PostgreSQL 17 runs on port 5432 **and can be exposed to the host**
- Database microservice runs on port 3002 **and can be exposed to the host**
- Migrations run automatically when the container starts (if PostgreSQL is enabled)
- Data persists in a named Docker volume
- Services can be enabled/disabled independently via environment variables

## Service Modes

The container supports three deployment modes via environment variables:

1. **Full Mode (default)**: Both PostgreSQL and microservice
   - `ENABLE_DB=true` and `ENABLE_DB_SERVICE=true`
   - Exposes both ports: 5432 (PostgreSQL) and 3002 (microservice)

2. **Database Only**: PostgreSQL without microservice
   - `ENABLE_DB=true` and `ENABLE_DB_SERVICE=false`
   - Exposes only port 5432 (PostgreSQL)

3. **Microservice Only**: Microservice without PostgreSQL
   - `ENABLE_DB=false` and `ENABLE_DB_SERVICE=true`
   - Exposes only port 3002 (microservice)
   - Requires external PostgreSQL connection via `DATABASE_URL`

## Quick Start

```bash
cd homelab-vm-provisioner-db

# Build image
./build --docker

# Start container (full mode: PostgreSQL + microservice)
./start --docker

# Verify health
curl http://localhost:3002/health

# Connect to PostgreSQL directly
psql postgresql://hlvmp:hlvmppass@localhost:5432/hlvmp

# View logs
docker logs hlvmp-db

# Stop container
docker stop hlvmp-db
```

## Service Mode Configuration

Set environment variables in `.env` to control which services run:

```bash
# Full mode (default) - both services
ENABLE_DB=true
ENABLE_DB_SERVICE=true
s:** 
- 3002 (microservice, when ENABLE_DB_SERVICE=true)
- 5432 (PostgreSQL, when ENABLE_DB=true
# Database only mode
ENABLE_DB=true
ENABLE_DB_SERVICE=false

# Microservice only mode (requires external PostgreSQL)
ENABLE_DB=false
ENABLE_DB_SERVICE=true
DATABASE_URL=postgresql://user:pass@external-host:5432/dbname
```

## Image Details

**Image name:** `hlvmp-db:latest`

**Base image:** `postgres:17`

**Additional components:**
- Node.js 20.x
- Express microservice
- Migration scripts

**Exposed port:** 3002 (microservice only)

**Volume:** `hlvmp-postgres-data` (PostgreSQL data directory)

## Environment Variables

Configure via `.env` file:
Service mode (default: both enabled)
ENABLE_DB=true              # Enable PostgreSQL
ENABLE_DB_SERVICE=true      # Enable microservice

# Microservice port (exposed when ENABLE_DB_SERVICE=true)
DB_SERVICE_PORT=3002

# PostgreSQL port mapping (exposed when ENABLE_DB=true)
POSTGRES_PORT=5432

# Microservice authentication (shared secret)
DB_SERVICE_PASSWORD=changeme_db_secret

# PostgreSQL credentials (internal or exposed based on ENABLE_DB)
POSTGRES_USER=hlvmp
POSTGRES_PASSWORD=hlvmppass
POSTGRES_DB=hlvmp

# Database connection URL (required when ENABLE_DB=false)
DATABASE_URL=postgresql://hlvmp:hlvmppass@localhost:5432/R=hlvmp
POSTGRES_PASSWORD=hlvmppass
POSTGRES_DB=hlvmp
```

## Container Lifecycle

### Build Image

```bash
./build --docker
```

Builds the `hlvmp-db:latest` image with:
- PostgreSQL 17 from base image
- Node.js 20.x installed v (depends on enabled services):

**Full mode (ENABLE_DB=true, ENABLE_DB_SERVICE=true):**
1. Initialize PostgreSQL data directory (if first run)
2. Start PostgreSQL server
3. Wait for PostgreSQL to be ready
4. Create database if it doesn't exist
5. Run pending migrations
6. Start microservice on port 3002
7. Expose both ports 5432 and 3002

**Database only mode (ENABLE_DB=true, ENABLE_DB_SERVICE=false):**
1. Initialize PostgreSQL data directory (if first run)
2. Start PostgreSQL server
3. Wait for PostgreSQL to be ready
4. Create database if it doesn't exist
5. Run pending migrations
6. Expose port 5432

**Microservice only mode (ENABLE_DB=false, ENABLE_DB_SERVICE=true):**
1. Connect to external PostgreSQL via DATABASE_URL
2. Start microservice on port 3002
3. Expose
./start --docker
```

Container startup sequence:
1. Initialize PostgreSQL data directory (if first run)
2. Start PostgreSQL server
3. Wait for PostgreSQL to be ready
4. Create database if it doesn't exist
5. Run pending migrations
6. Start microservice on port 3002

### Stop Container

```bash
docker stop hlvmp-db
```

Gracefully shuts down both PostgreSQL and the microservice.

### Remove Container

```bash
docker stop hlvmp-db
docker rm hlvmp-db
```

Data persists in the `hlvmp-postgres-data` volume.

### Remove Volume (Data)

```bash
docker stop hlvmp-db
docker rm hlvmp-db
docker volume rm hlvmp-postgres-data
```

**Warning:** This permanently deletes all database data.

## Accessing Services

### Microservice (from host)

```bash
# Health check (no auth required)
curl http://localhost:3002/health

# List jobs (requires auth)
curl -H "Authorization: Bearer changeme_db_secret" \
  http://localhost:3002/jobs

# Enqueue job (requires auth)
curl -X POST http://localhost:3002/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer changeme_db_secret" \
  -d '{"type":"provision_vm","targetHostId":"host1","payload":{}}'
```

**Note:** All endpoints except `/health` require authentication via the `Authorization` header.

### PostgreSQL (from inside container)

PostgreSQL is not exposed to the host. To access it:

```bash
# Connect via psql inside container
docker exec -it hlvmp-db psql -U hlvmp -d hlvmp

# Run SQL commands
docker exec hlvmp-db psql -U hlvmp -d hlvmp -c "SELECT * FROM jobs"
```

## Debugging

### View Logs

```bash
# All logs (PostgreSQL + microservice)
docker logs hlvmp-db

# Follow logs
docker logs -f hlvmp-db

# Last 50 lines
docker logs --tail 50 hlvmp-db
```

### Container Shell

```bash
# Get shell access
docker exec -it hlvmp-db bash

# Inside container:
ps aux                      # See running processes
psql -U hlvmp -d hlvmp      # Access PostgreSQL
curl localhost:3002/health  # Test microservice
```

### Rebuild Image

If you modify the microservice code:

```bash
# Stop and remove container
docker stop hlvmp-db
docker rm hlvmp-db

# Rebuild image
./build --docker

# Start new container
./start --docker
```

## Troubleshooting

### Container won't start

```bash
# Check if container name is already in use
docker ps -a | grep hlvmp-db

# Remove old container
docker rm hlvmp-db

# Try starting again
./start --docker
```

### Migrations fail

```bash
# Check logs
docker logs hlvmp-db

# Migrations run automatically on startup
# If they fail, the container will exit
# Fix the migration SQL, then rebuild and restart
```

### Can't connect to microservice

```bash
# Verify container is running
docker ps | grep hlvmp-db

# Check if port 3002 is bound
docker port hlvmp-db

# Test from inside container
docker exec hlvmp-db curl localhost:3002/health
```

### PostgreSQL data corruption

```bash
# Stop container
docker stop hlvmp-db

# Remove container and volume
docker rm hlvmp-db
docker volume rm hlvmp-postgres-data

# Start fresh
./start --docker
```

## Comparison: Docker vs Native

| Feature | Docker Mode | Native Mode |
|---------|-------------|-------------|
| **PostgreSQL** | Inside container | System service |
| **Microservice** | Inside container | npm start |
| **Port 5432** | Not exposed | Exposed |
| **Port 3002** | Exposed | Exposed |
| **Migrations** | Automatic on startup | Manual (npm run migrate) |
| **Setup** | Docker only | Full PostgreSQL install |
| **Performance** | Slight overhead | Native speed |
| **Use case** | Development | Production |

## Integration with API

The API service connects to the database microservice via HTTP:

```bash
# API .env
DB_SERVICE_URL=http://localhost:3002
```

Whether you run the database in Docker mode or native mode, the API always connects to the same microservice URL. The API doesn't need to know how PostgreSQL is running.

## Production Considerations

Docker mode is designed for development convenience. For production:

1. **Use native PostgreSQL** for better performance and reliability
2. **Use managed PostgreSQL** (AWS RDS, Google Cloud SQL, etc.)
3. **Run microservice as a systemd service** instead of in Docker
4. **Add TLS** for microservice communication
5. **Implement connection pooling** (PgBouncer)
6. **Set up replication** for high availability
7. **Monitor both PostgreSQL and microservice** health

The Docker mode is single-container for simplicity, which is fine for development but not recommended for production.
