# Token Efficiency Guide

## Architecture Benefits

This modular agent architecture is designed for **maximum token efficiency**:

### 🎯 Direct Specialist Access (Most Efficient)

**Best Practice**: Skip the orchestrator and go directly to the specialist agent for your project.

**Token Savings**: ~60-70% compared to loading generic instructions

**OpenCode**:
```
# Instead of orchestrator (141 lines)
@agents/test-writer.agent.md

# Go directly to specialist (188-237 lines of focused content)
@homelab-vm-provisioner-api/agents/test-writer.agent.md
@homelab-vm-provisioner-client/agents/test-writer.agent.md  
@homelab-vm-provisioner-api/homelab-vm-provisioner/agents/test-writer.agent.md
```

**Why This Is Efficient**:
- Loads ONLY the patterns for your specific project
- No generic multi-framework instructions
- No routing overhead
- Focused context = better results with fewer tokens

### 🔄 Via Orchestrator (Convenient but Uses More Tokens)

**When to Use**: When you're not sure which project or working across projects

**Token Cost**: Orchestrator (~70-140 lines) + Specialist (~100-220 lines) = ~170-360 lines total

**Trade-off**: Convenience vs. token usage

## Token Efficiency Comparison

| Approach | Tokens Used | Best For |
|----------|-------------|----------|
| Direct specialist | 60-240 lines | Single-project work (RECOMMENDED) |
| Via orchestrator | 130-360 lines | Cross-project or unclear scope |
| Old monolithic agent | 277-613+ lines | ❌ Removed, don't use |

## Optimization Strategies

### 1. Know Your Project

If you know which project you're working in:
```bash
# Working in API? Use API agent directly
cd homelab-vm-provisioner-api
@homelab-vm-provisioner-api/agents/test-writer.agent.md

# Working in Client? Use Client agent directly  
cd homelab-vm-provisioner-client
@homelab-vm-provisioner-client/agents/test-writer.agent.md
```

### 2. Use AGENTS.md for Quick Reference

The root `AGENTS.md` (~300 lines) provides:
- Project overview
- Quick command reference
- Architecture understanding

Load it ONCE at session start, then use specialists.

### 3. Avoid Redundant Loading

**Don't do this**:
```
1. Load AGENTS.md
2. Load orchestrator
3. Load specialist
```

**Do this instead**:
```
1. Load specialist directly OR
2. Load orchestrator (which will route to specialist)
```

### 4. Batch Related Operations

If making multiple changes in one project:
```
# Good: Load specialist once, do multiple operations
@homelab-vm-provisioner-api/agents/test-writer.agent.md
1. Write tests for validation.js
2. Write tests for network-model.js
3. Run coverage

# Bad: Load orchestrator for each operation (expensive)
```

## Current Agent Status

### ✅ All Agents Optimized (Modular Architecture Complete)

**Orchestrators** (avg ~82 lines each):
- **test-writer**: 141 lines → routes to specialists (188-237 lines)
- **coverage-runner**: 67 lines → routes to specialists (77-85 lines)
- **feature-developer**: 68 lines → routes to specialists (87-109 lines)
- **defect-fixer**: 67 lines → routes to specialists (59-70 lines)
- **doc-writer**: 66 lines → routes to specialists (82-124 lines)

**Specialists by Project**:
- **API** (homelab-vm-provisioner-api/agents/): 5 agents, 70-188 lines each
- **Client** (homelab-vm-provisioner-client/agents/): 5 agents, 59-237 lines each
- **Python** (homelab-vm-provisioner-api/homelab-vm-provisioner/agents/): 5 agents, 66-221 lines each

**Result**: ~60-70% token savings when using specialists directly vs orchestrator+specialist

## Token Savings Examples

### Example 1: Writing API Tests

**Old Monolithic Approach**:
- Load monolithic test-writer with ALL frameworks: ~500+ lines
- Includes React, Python, Playwright examples you don't need

**Via Orchestrator**:
- Load test-writer orchestrator: 141 lines
- Orchestrator routes to API specialist: 188 lines
- **Total**: 329 lines

**Direct Specialist (Most Efficient)**:
- Load API-specific test-writer: 188 lines
- Only vitest + supertest patterns for Express

**Savings**:
- Direct vs Monolithic: 188 vs 500+ = **62% savings**
- Direct vs Orchestrator: 188 vs 329 = **43% savings**

### Example 2: Running Coverage for Python Project

**Old Monolithic Approach**:
- Load coverage-runner with ALL project patterns: ~277 lines

**Via Orchestrator**:
- Load coverage-runner orchestrator: 67 lines
- Orchestrator routes to Python specialist: 85 lines
- **Total**: 152 lines

**Direct Specialist (Most Efficient)**:
- Load Python-specific coverage-runner: 85 lines
- Only unittest + coverage.py patterns

**Savings**:
- Direct vs Monolithic: 85 vs 277 = **69% savings**
- Direct vs Orchestrator: 85 vs 152 = **44% savings**

### Example 3: Cross-Project Feature

**Scenario**: Add VM tagging across Python → API → Client

**Efficient approach** (direct specialists):
1. Load Python specialist: ~109 lines → implement backend
2. Load API specialist: ~87 lines → add API endpoint
3. Load Client specialist: ~89 lines → add UI

**Total**: ~285 lines, staged across 3 focused sessions

**Via Orchestrators**:
1. Feature-developer orchestrator: 68 lines × 3 = 204 lines (routing overhead)
2. Plus specialists: 109 + 87 + 89 = 285 lines
**Total**: 489 lines

**Old Monolithic Approach**:
- Load one giant feature-developer: 389 lines per session × 3 = 1,167 lines
- Pay for patterns you don't use in each step

**Savings**: Direct specialists save **59% vs monolithic**, **42% vs orchestrators**

## Best Practices Summary

1. **🎯 Use specialists directly** when you know the project
2. **📍 Work in project directory** to make paths clearer
3. **♻️ Reuse loaded agents** for multiple related tasks
4. **🚫 Avoid stacking** orchestrator + specialist + AGENTS.md
5. **📊 Check line counts** - if an agent feels too large, it probably is

## Measuring Your Token Usage

Rough token estimation: **1 line ≈ 3-5 tokens**

| Agent Type | Lines | Est. Tokens | Use Case |
|------------|-------|-------------|----------|
| Specialist | ~200 | 600-1000 | Single project work ✅ |
| Orchestrator | ~140 | 420-700 | Project routing |
| Both | ~340 | 1020-1700 | Cross-project |
| Monolithic | 500+ | 1500-2500+ | ❌ Avoid |

## Future Optimizations

Once all agents are modular:
- Estimated token reduction: **50-70%** for focused tasks
- Faster responses: Less context to process
- Better results: More focused, less noise
