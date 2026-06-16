# Homelab VM Provisioner Monorepo

This workspace consists of three integrated projects:

- **homelab-vm-provisioner-api**: Node.js Express API (wraps Python CLI)
- **homelab-vm-provisioner-client**: React frontend (Material-UI)
- **homelab-vm-provisioner**: Python CLI for libvirt VM provisioning

## Architecture

### Component Boundaries

- **Python CLI**: Core provisioning logic, VM lifecycle management, nftables config
- **Node.js API**: HTTP layer, privilege management, YAML config store
- **React Client**: User interface for VM management

### Communication Flow

Client (React) → API (Express) → Python CLI (subprocess) → libvirt

## Build and Test

### Root Commands
```bash
./setup           # Initialize all subprojects
./start           # Start API and client dev servers
./build           # Build all projects with coverage + docs
```

### Subproject Commands

**API** (homelab-vm-provisioner-api/):
```bash
npm test          # Run vitest unit tests
npm run coverage  # Generate coverage report (>85% required)
npm run docs:build # Build JSDoc documentation
```

**Client** (homelab-vm-provisioner-client/):
```bash
npm test          # Run vitest component tests
npm run test:e2e  # Run Playwright end-to-end tests
npm run coverage  # Generate coverage report
npm run dev       # Start Vite dev server
```

**Python** (homelab-vm-provisioner-api/homelab-vm-provisioner/):
```bash
./scripts/test     # Run unittest suite
./scripts/coverage # Generate coverage report (>85% required)
./scripts/lint     # Run ruff linter
./scripts/docs-build # Build Sphinx documentation
```

## Code Style

### JavaScript/React
- ES modules (`type: "module"` in package.json)
- Vitest for testing with @testing-library/react
- Material-UI components, emotion styling
- Avoid direct node binary calls, use npm scripts

### Python
- Python 3.9+ compatible
- Ruff for linting (E, F, I rules)
- unittest framework (not pytest)
- Type hints optional but encouraged
- 100 character line length

## Testing Conventions

### What to Test
- **API**: Request validation, error handling, subprocess communication
- **Client**: Component behavior, user interactions, API integration
- **Python**: VM provisioning logic, config parsing, nftables generation

### Test Organization
- **API**: `test/*.test.js` (unit), uses supertest for HTTP
- **Client**: `test/*.test.jsx` (unit), `tests/e2e/*.spec.js` (Playwright)
- **Python**: `tests/test_*.py` (unittest), integration tests included

### Coverage Requirements
- Minimum 85% coverage for API and Python
- Run coverage before builds (enforced in build scripts)
- Coverage reports: `.build/coverage/` (Python), `coverage/` (JS)

## Documentation

### Standards
- **API**: JSDoc comments in source, documentation.js for HTML
- **Client**: JSDoc for complex functions, component prop documentation
- **Python**: Sphinx with RST, docstrings in Google style

### Build Locations
- API docs: `docs/_build/html/`
- Client docs: `docs/_build/html/`
- Python docs: `homelab-vm-provisioner/docs/_build/html/`

### When to Update Docs
- New API endpoints or public functions
- New CLI commands or configuration options
- Architecture changes or new components
- Before merging features

## Common Patterns

### Error Handling
- **API**: Return appropriate HTTP status codes (400, 500)
- **Python**: Raise descriptive exceptions, caught by CLI
- **Client**: Display user-friendly error messages

### Configuration
- **Python**: YAML config via `vmctl.yaml`, Jinja2 templates
- **API**: Config store in `config-store.js`, privilege checks
- **Client**: API base URL from environment

### Privilege Management
- API runs as non-root, elevates for specific operations
- Python CLI requires root for libvirt/nftables operations
- Client assumes no direct privilege escalation

## Specialized Agents

This workspace uses a modular agent architecture with orchestrators and specialists:

### Orchestrator Agents (`agents/`)
Top-level agents that route requests to specialized subproject agents:
- **test-writer**: Routes test writing to API/Client/Python specialists
- **coverage-runner**: Coordinates coverage analysis across projects
- **feature-developer**: Orchestrates cross-project feature development
- **defect-fixer**: Routes bugs to the appropriate project specialist
- **doc-writer**: Coordinates documentation across all projects

### Specialist Agents (per subproject)
Each subproject has its own specialized agents:
- **homelab-vm-provisioner-api/agents/**: Node.js/Express API specialists
- **homelab-vm-provisioner-client/agents/**: React/Material-UI specialists
- **homelab-vm-provisioner-api/homelab-vm-provisioner/agents/**: Python CLI specialists

### Token Efficiency

**💡 Recommended**: Use specialist agents directly for 60-70% token savings.

Instead of orchestrator + specialist, go directly to the project specialist:
```
# Most efficient (200 lines)
@homelab-vm-provisioner-api/agents/test-writer.agent.md

# Less efficient (340 lines = orchestrator + specialist)
@agents/test-writer.agent.md
```

See [agents/TOKEN_EFFICIENCY.md](agents/TOKEN_EFFICIENCY.md) for detailed optimization strategies.

### How to Use

**OpenCode**:
```
@agents/test-writer.agent.md Write tests for provision.py
@homelab-vm-provisioner-api/agents/test-writer.agent.md Write API tests
```

**GitHub Copilot**:
```
@test-writer Write tests for provision.py
@coverage-runner Check coverage for the API project
```

**Cursor**:
```
Use test-writer agent to create tests for provision.py
Add agents/test-writer.agent.md as context
```

**Windsurf**:
```
Load agents/test-writer.agent.md as cascade context
```

**Aider**:
```bash
aider --read agents/test-writer.agent.md provision.py
# Or go directly to specialist:
cd homelab-vm-provisioner-api
aider --read agents/test-writer.agent.md src/validation.js
```

See [agents/README.md](agents/README.md) for complete documentation on the modular architecture.

## Key Gotchas

### Node.js
- Don't use `node` directly in terminal, use npm scripts (handles paths correctly)
- Vitest runs in different context, import from actual modules not test paths
- Express async errors need proper error handling middleware

### Python
- Virtual environment must be activated or use scripts (handle resolution)
- Cloud-init templates require exact YAML structure
- libvirt operations fail silently if VMs already exist

### React
- Material-UI theme must wrap all components
- Vitest needs jsdom environment for DOM testing
- Playwright tests need dev server running

## Development Workflow

1. **Feature Development**: Start with tests, implement, verify coverage
2. **Bug Fixes**: Add regression test first, fix, verify test passes
3. **Documentation**: Update inline docs and rebuild HTML before commit
4. **Coverage Check**: Always run coverage before submitting
5. **Integration**: Test full stack (Python → API → Client) for user-facing changes
