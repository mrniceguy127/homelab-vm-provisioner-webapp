# Orchestrator Agents

This directory contains orchestrator agents that route requests to specialized subproject agents.

## Architecture

```
agents/ (this directory) - Orchestrators that delegate
├── test-writer.agent.md → Routes to subproject test writers
├── coverage-runner.agent.md → Coordinates coverage across projects  
├── feature-developer.agent.md → Orchestrates cross-project features
├── defect-fixer.agent.md → Routes bugs to appropriate project
└── doc-writer.agent.md → Coordinates documentation

homelab-vm-provisioner-api/agents/ - API-specific specialists
homelab-vm-provisioner-client/agents/ - Client-specific specialists
homelab-vm-provisioner-api/homelab-vm-provisioner/agents/ - Python-specific specialists
```

## How It Works

1. **Request comes in**: User asks to write tests, fix a bug, etc.
2. **Orchestrator identifies project**: Based on file path or description
3. **Delegates to specialist**: Routes to the appropriate subproject agent
4. **Specialist executes**: Uses project-specific patterns and conventions
5. **Result returned**: Complete, project-appropriate solution

## Benefits

- **Modular**: Each project has its own specialized agents
- **Maintainable**: Update one project's patterns without affecting others
- **Reusable**: Subproject agents work independently or via orchestrator
- **Token Efficient**: Only loads relevant context for the specific project (~60-70% token savings)

**💡 For maximum token efficiency**, use specialists directly instead of orchestrators. See [TOKEN_EFFICIENCY.md](TOKEN_EFFICIENCY.md) for details.

## Platform Support

> **Platform Support**: OpenCode • GitHub Copilot • Cursor • Windsurf • Aider • Continue.dev

All agents work across major AI coding platforms. OpenCode is the primary platform.

## Usage

### Via Orchestrator (Recommended)

**OpenCode**:
```
@agents/test-writer.agent.md Write tests for provision.py
```

**GitHub Copilot**:
```
@test-writer Write tests for the API validation module
```

**Cursor / Windsurf / Aider**:
Load the orchestrator agent and describe what you need.

### Direct to Specialist (Recommended for Token Efficiency)

**⚡ Most efficient**: Bypass the orchestrator and use specialists directly.

**Token Savings**: ~60-70% compared to orchestrator + specialist

**OpenCode**:
```
@homelab-vm-provisioner-api/agents/test-writer.agent.md
@homelab-vm-provisioner-client/agents/test-writer.agent.md  
@homelab-vm-provisioner-api/homelab-vm-provisioner/agents/test-writer.agent.md
```

This loads ONLY the patterns for your specific project, avoiding orchestrator overhead.

## Available Agents

| Orchestrator | Purpose | Delegates To |
|--------------|---------|-------------|
| test-writer | Write tests | API/Client/Python test writers |
| coverage-runner | Analyze coverage | API/Client/Python coverage runners |
| feature-developer | Implement features | API/Client/Python feature developers |
| defect-fixer | Fix bugs | API/Client/Python defect fixers |
| doc-writer | Write documentation | API/Client/Python doc writers |

See individual agent files for detailed usage and capabilities.
