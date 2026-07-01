# Homelab VM Provisioner Monorepo

Integrated monorepo for VM provisioning: Python CLI + Node.js API + React Client + Reverse Proxy

## Quick Start

```bash
./setup                    # Initialize submodules and call component setups
./setup --docker           # Setup for Docker mode (skip client/proxy npm install)
./setup --dev              # Setup with dev dependencies (for testing)
./setup --docker --dev     # Docker mode + dev dependencies on host (for testing)
./setup --client-only      # Setup for client-only development (skip API/provisioner)
./setup --skip-system-packages  # Skip system packages in all components

# Component-specific setup (each installs its own system packages)
cd homelab-vm-provisioner-api && ./setup [--skip-system-packages] [--dev]
cd homelab-vm-provisioner-client && ./setup [--skip-system-packages] [--skip-npm] [--skip-playwright]
cd homelab-vm-provisioner-proxy && ./setup [--skip-system-packages] [--skip-npm]
cd homelab-vm-provisioner-db && ./setup [--docker] [--skip-system-packages]
cd homelab-vm-provisioner-db-interface && ./setup [--docker] [--skip-system-packages] [--skip-npm]
cd homelab-vm-provisioner-job-queue && ./setup [--docker] [--skip-system-packages]
cd homelab-vm-provisioner-worker && ./setup [--skip-system-packages] [--dev]

./build                # Build all (docs + artifacts, no tests)
./build --docker       # Build with Docker for client static files
./build --client-only  # Build only client (skip API, for frontend-only dev)
./test                 # Run all tests with coverage report
./test --env           # Run tests for components enabled in .env
./test --cli           # Run only CLI tests
./test --worker        # Run only worker tests
./test --api           # Run only API tests
./test --client        # Run only client tests
./start                # Start all services (RabbitMQ, DB, API, worker, proxy)
./start --docker       # Start DB/API/proxy in Docker, worker locally
./docker-clean         # Stop and remove workspace Docker containers
./start --client-only  # Build client and start proxy only (no API, for remote API)
./homelab-vm-provisioner-client/build  # Build only client with Docker
./homelab-vm-provisioner-proxy/build   # Build proxy Docker image
./homelab-vm-provisioner-proxy/start   # Run proxy in Docker container
./homelab-vm-provisioner-job-queue/start  # Start RabbitMQ broker standalone
./homelab-vm-provisioner-worker/start  # Start worker daemon standalone
```

**Prerequisites:**
- Git (required by monorepo for submodule management)
- Docker (optional, required only for `--docker` mode)
  - **Installation is your responsibility**: Install Docker Desktop or Docker Engine before using Docker features

**Note**: The monorepo `./setup` script orchestrates component setups. Each component installs its own system packages. The project uses hierarchical `.env` configuration where component `.env` files override parent values through natural execution sequence (parent scripts source workspace `.env`, then call child scripts which source only their own `.env` and inherit remaining parent variables). Copy `.env.example` files to `.env` to customize configuration.

## Projects

| Project | Type | Testing |
|---------|------|---------|
| **homelab-vm-provisioner-cli** | Python CLI | unittest |
| **homelab-vm-provisioner-api** | Express API | vitest + supertest |
| **homelab-vm-provisioner-client** | React + Vite | vitest + Playwright |
| **homelab-vm-provisioner-proxy** | Reverse Proxy | none (dead simple) |
| **homelab-vm-provisioner-db** | PostgreSQL Infrastructure | schema verification (`./test`) |
| **homelab-vm-provisioner-db-interface** | Express DB API | node:test |
| **homelab-vm-provisioner-job-queue** | RabbitMQ Infrastructure | none (broker management) |
| **homelab-vm-provisioner-worker** | Python Worker Daemon | unittest |

## Architecture

```
                                          ┌→ db-interface (3002) → PostgreSQL (5432)
                                          │     (jobs, events, resource locks)
Browser → Proxy (3000) → API (3001) ──────┤
         ↓                     ↓            └→ RabbitMQ (3334) ───┐  publish (AMQP)
      Static Files      Python CLI            (job queue exchange) │
                            ↓                                      ↓  consume (AMQP)
                        libvirt                          Worker Daemon (Python)
                                                            ↓ runs vmctl CLI
                                                         libvirt / nftables
```

The API publishes each job to a RabbitMQ topic exchange (routing key `host.<HOST_ID>`)
and records job metadata via the db-interface microservice. The Worker consumes from its host-specific
queue, fetches job details from the API, acquires resource locks via the db-interface,
executes the CLI, and updates job status. PostgreSQL is no longer polled for job delivery.

**Component Roles**:
- **Proxy**: Dead-simple reverse proxy serving static files and proxying API requests
- **Python CLI**: Core provisioning, VM lifecycle, nftables
- **Worker Daemon**: Long-running process that consumes jobs from RabbitMQ and executes them
- **Node.js API**: HTTP layer, privilege management, config store, job publisher (RabbitMQ) + db-interface client
- **React Client**: User interface, Material-UI
- **Job Queue (RabbitMQ)**: Topic exchange and per-host queues for async job delivery
- **DB Interface (microservice)**: HTTP REST layer over PostgreSQL — job metadata, event log, resource lock operations
- **PostgreSQL (DB component)**: Database engine + migrations; job metadata store, event log, resource locks (not the delivery queue)

## Database Setup

The database is split into two components:
- **homelab-vm-provisioner-db**: PostgreSQL engine + SQL migrations (schema).
- **homelab-vm-provisioner-db-interface**: HTTP REST microservice (port 3002) in
  front of PostgreSQL, used by the API and worker.

Job **delivery** is handled by RabbitMQ (see Job Queue Setup), not by polling
PostgreSQL. Native PostgreSQL is the default:

```bash
# 1. PostgreSQL engine + migrations (native, recommended for production)
cd homelab-vm-provisioner-db
./setup              # Install PostgreSQL

# Create database and user (first install only)
sudo -u postgres psql -c "CREATE DATABASE hlvmp;"
sudo -u postgres psql -c "CREATE USER hlvmp WITH PASSWORD 'hlvmppass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE hlvmp TO hlvmp;"

./start              # Start PostgreSQL service
./build              # Run migrations (schema provisioning)
./test               # Verify connectivity + schema

# 2. db-interface microservice
cd ../homelab-vm-provisioner-db-interface
./setup              # Install Node.js + npm dependencies
./start              # Start microservice (port 3002)

# Verify DB_SERVICE_HOST/DB_SERVICE_PORT and DB_SERVICE_PASSWORD are set in API .env
# DB_SERVICE_HOST=localhost
# DB_SERVICE_PORT=3002
# DB_SERVICE_PASSWORD=changeme_db_secret
```

Docker mode is available for development (two separate images):

```bash
# PostgreSQL (migrations run automatically on startup)
cd homelab-vm-provisioner-db
./setup --docker
./build --docker     # Build hlvmp-db image
./start --docker     # Start hlvmp-db container (port 5432)

# db-interface (node-only image, connects to external PostgreSQL)
cd ../homelab-vm-provisioner-db-interface
./setup --docker
./build --docker     # Build hlvmp-db-interface image
./start --docker     # Start hlvmp-db-interface container (port 3002)
```

**db-interface Architecture:**
- The db-interface microservice (port 3002) is an **internal API** used by the main API and worker
- It is **not exposed to external users** - only the API/worker communicate with it
- It connects to PostgreSQL (managed by the `homelab-vm-provisioner-db` component)
- Authentication required via `DB_SERVICE_PASSWORD` shared secret for all endpoints except `/health`
- PostgreSQL install, service lifecycle, and migrations live in `homelab-vm-provisioner-db`

## Job Queue Setup

Async job delivery uses a RabbitMQ broker managed by the `homelab-vm-provisioner-job-queue`
component. The API publishes jobs to a topic exchange; each worker consumes from its
own host-specific queue.

```bash
cd homelab-vm-provisioner-job-queue
./setup              # Install RabbitMQ (native)
./setup --docker     # Or run RabbitMQ in Docker
./start              # Start the broker
./build              # Provision topology (vhost, users, exchange, per-host queues)
./test               # Verify topology health
```

**Topology:**
- Virtual host: `provisioner`
- Exchange: `provisioner.jobs` (topic)
- Routing key: `host.<HOST_ID>` (e.g. `host.local`)
- Queue: `provisioner.worker.<HOST_ID>` (e.g. `provisioner.worker.local`)
- AMQP port: `QUEUE_PORT` (default 3334); management UI: `QUEUE_MGMT_PORT` (default 13334)

**Credentials** (three isolated users):
- `QUEUE_ADMIN_USER` — topology provisioning (setup/build only)
- `QUEUE_API_USER` — publish-only, used by the API
- `QUEUE_USER` — consume-only from the host queue, used by the Worker

**Disable Job Queue**: Set `ENABLE_JOB_QUEUE=false` in workspace `.env`.

## Worker Daemon
Standalone Python service that consumes jobs from RabbitMQ and executes them:

```bash
# Setup and start via monorepo (worker enabled by default)
./setup
./start

# Or setup and start standalone (run from worker directory)
cd homelab-vm-provisioner-worker
./setup

# Configure environment
cp .env.example .env
# Edit .env: set HOST_ID, DB_SERVICE_HOST, DB_SERVICE_PASSWORD

# Start worker standalone
./start
```

**Worker Configuration:**
- `HOST_ID`: Host identifier for job routing/claiming (required)
- `QUEUE_HOST`: RabbitMQ host (required)
- `QUEUE_PORT`: RabbitMQ AMQP port (default: 3334)
- `QUEUE_VHOST`: RabbitMQ virtual host (default: provisioner)
- `QUEUE_NAME`: Host-specific queue to consume (default: provisioner.worker.<HOST_ID>)
- `QUEUE_USER` / `QUEUE_PASSWORD`: Worker consumer credentials (read-only)
- `DB_SERVICE_HOST`: Database microservice host (required)
- `DB_SERVICE_PORT`: Database microservice port (default: 3002)
- `DB_SERVICE_PASSWORD`: Database microservice password (required)
- `API_HOST` / `API_PORT`: API used to fetch/update job details (required)
- `PROVISIONER_CLI_PATH`: Path to provisioner CLI (required; monorepo sets this automatically)
- `PROVISIONER_CONCURRENCY`: Max concurrent jobs (default: 1)
- `WORKER_STATE_REFRESH_INTERVAL`: Runtime-state refresh interval in seconds (default: 60.0)

**Monorepo vs Standalone:**
- **Monorepo mode**: Worker enabled by default, uses `../homelab-vm-provisioner-cli` via `PROVISIONER_CLI_PATH`
- **Standalone mode**: `PROVISIONER_CLI_PATH` must be set explicitly to the provisioner CLI checkout
- **Disable Worker**: Set `ENABLE_WORKER=false` in workspace `.env` to disable

See [homelab-vm-provisioner-worker/README.md](homelab-vm-provisioner-worker/README.md) for full documentation.

## Code Style Essentials

**JavaScript**: ES modules, vitest, async/await, no defaults  
**React**: Material-UI, ThemeProvider required, Playwright for E2E  
**Python**: 3.9+, unittest (NOT pytest), ruff (linting required), Google-style docstrings

## Instruction Priority

When working inside a subproject, prefer that subproject's `AGENTS.md` for project-specific commands, framework rules, and testing patterns.

Do not assume patterns from one subproject apply to another. For example, Python uses `unittest`, the API uses `vitest`, and the client uses React testing patterns.

**Monorepo Role**: The workspace root is just an orchestrator. It does NOT install system packages. All system package installation is delegated to component setup scripts.

## AI Agents

Each project has OpenCode agents in its `.opencode/agents/` directory.

See each project's AGENTS.md for usage instructions and available agents.

## Testing Philosophy

1. **TDD**: Write tests first
2. **Coverage**: 80% minimum (enforced in API, Python CLI, & Worker)
3. **Integration**: Test full stack for user-facing features
4. **E2E**: Playwright for critical workflows (Client)

## Common Gotchas

**Python**: unittest not pytest, mock libvirt, 80% enforced in CLI & Worker, linting runs before tests  
**Node.js**: Use npm scripts not node binary, vitest context differs  
**React**: ThemeProvider required, Playwright needs dev server running

## Documentation Sources

Do not duplicate generated API, CLI, or component documentation in `AGENTS.md`.

Use the repo's actual documentation sources and build configuration. Prefer source doc comments, RST/Markdown docs, and generated documentation outputs where present.

When changing public behavior:
- Locate the relevant source docs/comments for that subproject.
- Update the docs source, not just generated output.
- Run the subproject's docs build command if one exists.
- Do not duplicate full generated documentation in `AGENTS.md`.
