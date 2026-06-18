# homelab-vm-provisioner

Top-level workspace for the homelab VM provisioner web application.

This repository wires together:

- `homelab-vm-provisioner-api/`: the Express API and nested Python provisioner integration
- `homelab-vm-provisioner-client/`: the React UI
- `homelab-vm-provisioner-proxy/`: a dead-simple reverse proxy that serves the React client and proxies API requests
- root scripts that install dependencies, build both apps, run tests, and deploy the client bundle into the proxy's `public/` directory

The sub-repositories already contain their own detailed READMEs. This document covers the root project workflow.

## Architecture

```text
Browser → Proxy (port 3000) → API (port 3001) → Python CLI → libvirt
         ↓
      Static Files (React app)
```

## Workspace Layout

```text
.
|- homelab-vm-provisioner-api/
|  |- setup              # Setup API and Python provisioner
|  `- ...
|- homelab-vm-provisioner-client/
|  |- setup              # Setup client environment
|  |- build              # Build with Docker
|  `- ...
|- homelab-vm-provisioner-proxy/
|  |- setup              # Setup proxy environment
|  |- build              # Build Docker image
|  |- start              # Run in Docker
|  `- ...
|- .env.example
|- DOCKER.md
|- setup                 # Orchestrates all component setups
|- build                 # Orchestrates all builds
|- start                 # Starts all services
|- test                  # Runs all tests (supports --cli, --worker, --api, --client flags)
|- scripts/
|  `- test-docker-mode   # Test Docker setup
`- README.md
```

## Requirements

- Git with submodule support
- Node.js 18+
- npm
- Python 3 with `venv`
- Docker (optional, for containerized client builds)
- A Linux libvirt host if you want actual VM lifecycle operations to work end-to-end
- `sudo` access for the account running the API

Notes:

- Initialize submodules before the first root setup run.
- The workspace setup installs all system dependencies on supported Linux distributions: git, Node.js 18+, npm, Python, libvirt, qemu, nftables, and other VM provisioning tools.
- Supported distributions: Ubuntu/Debian, Fedora, RHEL/Rocky/AlmaLinux, Arch Linux.
- On machines where system packages are already installed, use `./setup --skip-system-packages`.

## Setup

### Prerequisites

**Required:**
- Git (for cloning and submodule management)

**Component-specific:**
- Each component will install its own system dependencies when you run its `./setup` script
- See "Component-specific setup" section below for details

**Optional:**
- Docker (if using `--docker` mode for client builds or proxy deployment)
  - **Note**: Docker installation is your responsibility. Install Docker Desktop (macOS/Windows) or Docker Engine (Linux) before running `./setup --docker`

### Fresh workspace setup

If you did not clone the repository with submodules, initialize them first:

```bash
git submodule update --init --recursive
```

Then run:

```bash
./setup
```

For Docker deployment mode:

```bash
./setup --docker
```

If you are cloning fresh, `git clone --recurse-submodules <repo>` is the simplest starting point.

What it does:

- initializes git submodules
- calls component setup scripts:
  - `homelab-vm-provisioner-api/setup` - installs system packages (Node.js, Python, libvirt, qemu, nftables) and sets up Python provisioner
  - `homelab-vm-provisioner-client/setup` - installs system packages (Node.js, npm) and client dependencies
  - `homelab-vm-provisioner-proxy/setup` - installs system packages (Node.js, npm) and proxy dependencies

**Note**: The monorepo `./setup` script is just an orchestrator. It delegates all system package installation to the component scripts.

### Component-specific setup

Each component can be set up independently with its own system package requirements:

```bash
# Setup API and Python provisioner
cd homelab-vm-provisioner-api
./setup                     # Install all system packages (Node.js, Python, libvirt, qemu, nftables)
./setup --skip-system-packages  # Skip system packages (assume already installed)
./setup --dev               # Install with dev dependencies

# Setup client
cd homelab-vm-provisioner-client
./setup                     # Install system packages (Node.js, npm)
./setup --skip-system-packages  # Skip system packages
./setup --skip-npm          # Skip npm install (for Docker builds)
./setup --skip-playwright   # Skip Playwright browser installation

# Setup proxy
cd homelab-vm-provisioner-proxy
./setup                     # Install system packages (Node.js, npm)
./setup --skip-system-packages  # Skip system packages
./setup --skip-npm          # Skip npm install (for Docker runtime)
```

**System packages installed by each component:**

- **API**: git, curl, Node.js 18+, npm, Python 3, pip, venv, libvirt, qemu, nftables, cloud-image-utils, openssh, wget
  - Also enables and starts libvirtd service
- **Client**: git, curl, Node.js 18+, npm
- **Proxy**: git, curl, Node.js 18+, npm
- **Python Provisioner** (nested in API): Python 3, pip, venv, libvirt, qemu, nftables, cloud-image-utils, openssh, wget
  - Also enables and starts libvirtd service

**Supported Linux distributions:**
- Ubuntu/Debian (Node.js from NodeSource)
- Fedora (native packages)
- RHEL/Rocky/AlmaLinux (EPEL + NodeSource)
- Arch Linux (native packages)

If your machine already has the required OS packages, use:

```bash
./setup --skip-system-packages
```

Useful pass-through options supported by the nested provisioner setup:

- `--skip-system-packages`: skip system package installation
- `--dev`: install Python dev dependencies (ruff, coverage, Sphinx)
- `--python <binary>`: specify Python interpreter

Note: The `--dev` flag installs dev dependencies in the Python provisioner and, when combined with `--docker`, also installs client and proxy npm packages on the host for testing (since tests don't run in containers).

Example:

```bash
./setup --skip-system-packages --python python3
```

## Configuration

The root project mostly works out of the box. The main configuration points are the root scripts and a small set of environment variables.

### Build Modes

The monorepo supports flexible deployment modes controlled by environment variables in `.env`. This allows you to enable/disable specific services:

**Environment variables:**
```bash
ENABLE_CLIENT=true       # React frontend + reverse proxy
ENABLE_API=true          # Express API + Python provisioner  
ENABLE_DB_SERVICE=true   # Node.js microservice for job queue
ENABLE_DB=true           # PostgreSQL database
```

**Common deployment modes:**

1. **Full stack (default)**: All services enabled
   ```bash
   # All variables true (default)
   ./setup && ./build && ./start
   ```

2. **Client only**: Frontend connecting to remote API
   ```bash
   ENABLE_CLIENT=true
   ENABLE_API=false
   ENABLE_DB_SERVICE=false
   ENABLE_DB=false
   
   # Or use legacy flag:
   ./setup --client-only
   ./build --client-only
   PROXY_API_HOST=http://remote-api:3001 ./start --client-only
   ```

3. **API only**: Backend without frontend
   ```bash
   ENABLE_CLIENT=false
   ENABLE_API=true
   ENABLE_DB_SERVICE=true
   ENABLE_DB=true
   
   ./setup && ./build && ./start
   # API on port 3001, DB service on 3002
   ```

4. **Database standalone**: PostgreSQL + microservice only
   ```bash
   ENABLE_CLIENT=false
   ENABLE_API=false
   ENABLE_DB_SERVICE=true
   ENABLE_DB=true
   
   cd homelab-vm-provisioner-db
   ./setup && ./build --docker && ./start --docker
   ```

5. **Database service only**: Microservice without PostgreSQL (requires external DB)
   ```bash
   ENABLE_DB_SERVICE=true
   ENABLE_DB=false
   DATABASE_URL=postgresql://user:pass@external-host:5432/dbname
   
   # Microservice connects to external PostgreSQL
   ```

6. **PostgreSQL only**: Database without microservice
   ```bash
   ENABLE_DB=true
   ENABLE_DB_SERVICE=false
   
   # Exposes PostgreSQL port 5432
   ```

**Setting modes:** Copy `.env.example` to `.env` and set the desired flags, or export them in your shell:

```bash
cp .env.example .env
# Edit .env to set ENABLE_* variables

# Or export directly:
export ENABLE_CLIENT=true ENABLE_API=false
./setup && ./build && ./start
```

**Legacy flag support:** The `--client-only` flag is still supported and automatically sets the appropriate mode flags.

### Root scripts

- `./setup`: installs dependencies and configures environments (git submodules, Python venv, npm packages, Playwright)
- `./setup --docker`: setup for Docker mode (skips client and proxy npm installs since they run in containers)
- `./setup --dev`: setup with dev dependencies for the Python provisioner
- `./setup --docker --dev`: Docker mode with dev dependencies installed on host for testing
- `./build`: builds documentation and app artifacts (no tests)
- `./build --docker`: builds client static files using Docker instead of local Node.js
- `./homelab-vm-provisioner-client/build`: standalone script to build only client static files with Docker
- `./homelab-vm-provisioner-proxy/build`: builds the proxy Docker image
- `./homelab-vm-provisioner-db/build --docker`: builds the database Docker image
- `./test`: runs all tests with coverage across Python CLI, Worker, API, and Client (supports `--cli`, `--worker`, `--api`, `--client` flags for selective testing, or `--env` to test only components enabled in `.env`)
- `./start`: starts enabled services (controlled by ENABLE_* variables in .env)
- `./start --docker`: starts services with Docker proxy (controlled by ENABLE_* variables)
- `./homelab-vm-provisioner-proxy/start`: runs the proxy in a Docker container (requires static files in `public/`)
- `./homelab-vm-provisioner-db/start --docker`: runs PostgreSQL and/or microservice in Docker container

**Note:** Build modes are controlled by environment variables (`ENABLE_CLIENT`, `ENABLE_API`, `ENABLE_DB_SERVICE`, `ENABLE_DB`). See the "Build Modes" section above.

### Docker commands

```bash
# Setup for Docker mode
./setup --docker

# Build Docker images
./homelab-vm-provisioner-client/build   # Build client static files
./homelab-vm-provisioner-proxy/build    # Build proxy image
./homelab-vm-provisioner-db/build --docker  # Build database image

# Start services in Docker
./start --docker                        # All enabled services
./homelab-vm-provisioner-proxy/start    # Proxy only
./homelab-vm-provisioner-db/start --docker  # Database service
```

### Client-only workflow (frontend development)

For frontend developers who don't need the full API stack locally:

**Using environment variables (recommended):**
```bash
# .env file
ENABLE_CLIENT=true
ENABLE_API=false
ENABLE_DB_SERVICE=false
ENABLE_DB=false
PROXY_API_HOST=http://remote-api-server:3001

./setup
./build
./start
```

**Using legacy --client-only flag:**
```bash
# One-time setup (skips Python provisioner and API dependencies)
./setup --client-only

# Build and start (connects to remote API)
./build --client-only
PROXY_API_HOST=http://192.168.1.100 ./start --client-only

# Or combine with Docker
./setup --client-only --docker
./build --client-only --docker
./start --client-only --docker
```

**Configuration**: Copy `.env.example` to `.env` and customize:
```bash
cp .env.example .env
# Edit .env to set PROXY_PORT, API_PORT, PROXY_API_HOST, etc.
```

Or set environment variables directly:
```bash
PROXY_PORT=8080 API_PORT=8081 ./start --docker
```

### Environment Variables (.env)

The project uses a **hierarchical .env configuration system** where component `.env` files override parent values through natural script execution sequence:

**Structure:**
```
workspace/.env                                    # Loaded by workspace scripts
├── homelab-vm-provisioner-api/.env              # Loaded by API scripts (overrides workspace)
│   └── homelab-vm-provisioner-cli/.env          # Loaded by provisioner scripts (overrides API & workspace)
├── homelab-vm-provisioner-client/.env           # Loaded by client scripts (overrides workspace)
└── homelab-vm-provisioner-proxy/.env            # Loaded by proxy scripts (overrides workspace)
```

**How hierarchy works:**
1. Parent script sources workspace `.env`
2. Parent script calls child script (child inherits environment variables)
3. Child script sources only its own `.env` (overrides inherited values)
4. Variables not in child `.env` remain from parent (inheritance)

**Example execution flow:**
```bash
./setup
  ├─ Sources workspace/.env (API_PORT=3001, PROXY_PORT=3000)
  ├─ Calls homelab-vm-provisioner-api/setup
  │   ├─ Inherits API_PORT=3001, PROXY_PORT=3000
  │   ├─ Sources api/.env (API_PORT=4001)  # Override
  │   └─ Result: API_PORT=4001, PROXY_PORT=3000  # Kept from parent
  └─ Calls homelab-vm-provisioner-proxy/setup
      ├─ Inherits API_PORT=3001, PROXY_PORT=3000
      ├─ Sources proxy/.env (PROXY_PORT=8080)  # Override
      └─ Result: API_PORT=3001, PROXY_PORT=8080  # Kept from parent
```

**Key principle:** Children never load parent `.env` files. They only load their own. Hierarchy happens naturally through execution sequence and environment variable inheritance.

**Setup:**
```bash
# Copy all example files
cp .env.example .env
cp homelab-vm-provisioner-api/.env.example homelab-vm-provisioner-api/.env
cp homelab-vm-provisioner-client/.env.example homelab-vm-provisioner-client/.env
cp homelab-vm-provisioner-proxy/.env.example homelab-vm-provisioner-proxy/.env
cp homelab-vm-provisioner-api/homelab-vm-provisioner-cli/.env.example homelab-vm-provisioner-api/homelab-vm-provisioner-cli/.env

# Customize as needed
```

**Variable ownership:**
- **Workspace**: Sets defaults for all components
- **Components**: Override specific values, inherit the rest
- **Example**: Set `API_PORT=3001` in workspace, override with `API_PORT=4001` in API component

**Common variables:**
- `PROXY_PORT` - Proxy server port (default: 3000)
- `API_PORT` - API server port (default: 3001)
- `PROXY_API_HOST` - API host for proxy (default: http://172.17.0.1 for Docker, http://localhost for native)
- `PROVISIONER_VENV_DIR` - Python provisioner virtualenv path
- `HLVMP_NETWORK_POOL_CIDR` - VM network pool CIDR
- `HLVMP_NETWORK_GROUP_PREFIX_LENGTH` - VM network group prefix length

### Client-only mode (remote API)

Use `--client-only` to run just the frontend proxy without starting the local API. This is useful for:
- Connecting to a remote API server
- Frontend development without running the full stack locally
- Multiple developers sharing a single API instance

```bash
# Build client and start proxy, connecting to remote API
PROXY_API_HOST=http://192.168.1.100 ./start --client-only

# Or configure in .env
echo "PROXY_API_HOST=http://remote-server" >> .env
echo "API_PORT=3001" >> .env
./start --client-only

# With Docker proxy
./start --client-only --docker
```

The `--client-only` flag:
1. Builds the client (locally or with Docker if `--docker` is specified)
2. Deploys static files to the proxy
3. Starts only the proxy (skips API startup)
4. Uses `PROXY_API_HOST` and `API_PORT` to construct the API URL

### Environment variables

| Variable | Default | Used by | Purpose |
| --- | --- | --- | --- |
| `PROVISIONER_VENV_DIR` | `homelab-vm-provisioner-api/homelab-vm-provisioner-cli/.venv` | `./setup`, `./start` | Location of the nested Python provisioner virtual environment |
| `PORT` | `3000` (proxy), `3001` (API) | Proxy and API | HTTP ports for the services |
| `API_URL` | `http://localhost:3001` | Proxy | Backend API URL (constructed from PROXY_API_HOST + API_PORT) |
| `HLVMP_PROVISIONER_DIR` | `homelab-vm-provisioner-api/homelab-vm-provisioner-cli` | API | Override the nested provisioner checkout path |
| `HLVMP_API_RUNTIME_DIR` | `homelab-vm-provisioner-api/runtime` | API | Legacy runtime directory used for startup migration |
| `HLVMP_NETWORK_POOL_CIDR` | `10.80.0.0/16` | API | Global private pool used to allocate per-network-group subnets |
| `HLVMP_NETWORK_GROUP_PREFIX_LENGTH` | `28` | API | Prefix length allocated to each managed network group |
| `HLVMP_PYTHON_BIN` | set automatically by `./start` | API | Python executable used by the API bridge |
| `VITE_API_BASE_URL` | unset | client dev/build | Optional API base URL when running the client separately from the API |

Examples:

```bash
PROVISIONER_VENV_DIR="$HOME/.local/share/hlvmp/.venv" ./setup --skip-system-packages
PORT=4000 ./start
VITE_API_BASE_URL=http://localhost:3000 npm --prefix homelab-vm-provisioner-client run dev
```

### Generated and runtime paths

After setup and use, the workspace relies on these paths:

- `homelab-vm-provisioner-proxy/public/`: deployed client bundle served by the reverse proxy
- `homelab-vm-provisioner-api/homelab-vm-provisioner-cli/configs/`: saved VM YAML configs
- `homelab-vm-provisioner-api/homelab-vm-provisioner-cli/vm/metadata/`: persisted tenant and network-group records
- `homelab-vm-provisioner-api/homelab-vm-provisioner-cli/vm/keys/users/`: uploaded SSH public keys
- `homelab-vm-provisioner-api/homelab-vm-provisioner-cli/vm/data/`: provisioner VM data

## Tenant Networking

The workspace now uses tenant-owned network groups instead of one flat VM network.

- each network group maps to one libvirt network and one small subnet, default `/28`
- new groups allocate subnets from `HLVMP_NETWORK_POOL_CIDR`, default `10.80.0.0/16`
- VMs in the same group can talk by default
- hypervisor host access is allowed by default and can be disabled per VM
- cross-group traffic is denied by default
- private LAN access is denied by default and can be enabled per VM for admin-owned VMs
- internet egress is available through NAT-backed profiles without exposing private RFC1918 LANs by default

Managed VM and network-group policy now reconciles through application-owned nftables tables. See `homelab-vm-provisioner-api/docs/vm-networking-nftables.md`.

## Running

### Bundled root-project run

After `./setup` completes, build and start the workspace from the root with:

```bash
./build
./start
```

This command:

- verifies the built client exists in `homelab-vm-provisioner-api/public/`
- verifies the nested provisioner virtual environment exists
- exports `HLVMP_PYTHON_BIN` to the provisioner venv's Python interpreter
- starts the API, which also serves the built client

Open:

```text
http://localhost:3000
```

Notes:

- Start the API from an interactive terminal.
- On startup, the API may prompt for `sudo` so later `virsh` and libvirt operations can run correctly.

### Split development mode

If you want live frontend reloads, run the API and client separately.

Terminal 1:

```bash
./start
```

Terminal 2:

```bash
npm --prefix homelab-vm-provisioner-client run dev
```

Then open:

```text
http://localhost:5173
```

By default, the Vite dev server proxies `/api` and `/health` to `http://localhost:3000`.

If the API is running elsewhere, set `VITE_API_BASE_URL` before starting the client.

## Rebuilding

To rerun the root build without reinstalling dependencies:

```bash
./build
```

This runs:

- API tests, coverage, and docs build
- client tests, coverage, app build, and docs build
- client Playwright e2e tests
- client bundle deployment into the API `public/` directory

## Testing

To run tests across all subprojects and see a consolidated coverage report:

```bash
./test              # Run all tests
./test --cli        # Run only CLI tests
./test --worker     # Run only Worker tests
```

This runs:

- Python CLI tests with coverage (homelab-vm-provisioner-cli)
- Node.js API tests with coverage (homelab-vm-provisioner-api)
- React Client tests with coverage (homelab-vm-provisioner-client)

The script displays a color-coded summary showing:

- Test pass/fail status for each project
- Number of tests run
- Coverage percentage for each project
- Overall workspace test health

Example output:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1/3 Python CLI (homelab-vm-provisioner-cli)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Python CLI
  Tests:    275 tests (all passed)
  Coverage: 86%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  2/3 Node.js API (homelab-vm-provisioner-api)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Node.js API
  Tests:    111 tests passed
  Coverage: 87.09%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  3/3 React Client (homelab-vm-provisioner-client)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ React Client
  Tests:    31 tests passed
  Coverage: 74.64%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✓ Python CLI: 275 tests (all passed), Coverage 86%
  ✓ Node.js API: 111 tests passed, Coverage 87.09%
  ✓ React Client: 31 tests passed, Coverage 74.64%

✓ All tests passed!
```

For individual project testing, see the respective subproject documentation.

## Subproject Docs

For service-specific details, see:

- `homelab-vm-provisioner-api/README.md`
- `homelab-vm-provisioner-client/README.md`
