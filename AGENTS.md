# Homelab VM Provisioner Monorepo

Integrated monorepo for VM provisioning: Python CLI + Node.js API + React Client + Reverse Proxy

## Quick Start

## Quick Start

```bash
./setup                # Initialize submodules and call component setups
./setup --docker       # Setup for Docker mode (skip client/proxy npm install)
./setup --dev          # Setup with dev dependencies (for testing)
./setup --docker --dev # Docker mode + dev dependencies on host (for testing)
./setup --client-only  # Setup for client-only development (skip API/provisioner)
./setup --skip-system-packages  # Skip system packages in all components

# Component-specific setup (each installs its own system packages)
cd homelab-vm-provisioner-api && ./setup [--skip-system-packages] [--dev]
cd homelab-vm-provisioner-client && ./setup [--skip-system-packages] [--skip-npm] [--skip-playwright]
cd homelab-vm-provisioner-proxy && ./setup [--skip-system-packages] [--skip-npm]

./build                # Build all (docs + artifacts, no tests)
./build --docker       # Build with Docker for client static files
./build --client-only  # Build only client (skip API, for frontend-only dev)
./test-all             # Run all tests with coverage report
./start                # Start proxy (port 3000) and API (port 3001) - local
./start --docker       # Start API locally, proxy in Docker
./start --client-only  # Build client and start proxy only (no API, for remote API)
./homelab-vm-provisioner-client/build  # Build only client with Docker
./homelab-vm-provisioner-proxy/build   # Build proxy Docker image
./homelab-vm-provisioner-proxy/start   # Run proxy in Docker container
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

## Architecture

```
Browser → Proxy (port 3000) → API (port 3001) → Python CLI → libvirt
         ↓
      Static Files (React app from public/)
```

**Component Roles**:
- **Proxy**: Dead-simple reverse proxy serving static files and proxying API requests
- **Python CLI**: Core provisioning, VM lifecycle, nftables
- **Node.js API**: HTTP layer, privilege management, config store
- **React Client**: User interface, Material-UI

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
2. **Coverage**: 80% minimum (enforced in API & Python)
3. **Integration**: Test full stack for user-facing features
4. **E2E**: Playwright for critical workflows (Client)

## Common Gotchas

**Python**: unittest not pytest, mock libvirt, 80% enforced, linting runs before tests  
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
