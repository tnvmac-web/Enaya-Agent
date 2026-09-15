# HERMES.md - Enaya Agent Project Context

## Project Overview
Enaya Agent — Task-delegation AI agent with multi-agent orchestration, deep research, and structured planning.

## Architecture
- **Core**: Fork of Hermes Agent architecture (AIAgent, conversation_loop, prompt_builder, context_compressor)
- **Providers**: 15+ via shared runtime resolver (OpenRouter, Anthropic, OpenAI, NVIDIA, Google, Ollama, LM Studio)
- **Memory**: 5-layer (Session, Episodic, Semantic, Procedural, Project) — SQLite + ChromaDB
- **Tools**: 50+ across 6 toolsets (core, research, planning, delegation, synthesis, codebase)
- **Delegation**: Native subagent orchestration with DelegationOrchestrator, TaskQueue, ResultAggregator
- **Interfaces**: CLI, ACP, API Server, optional Gateway

## Key Conventions
- **Type hints** on all public functions
- **Error handling**: Catch exceptions, return JSON error strings from tools
- **Tool registration**: Auto-discovery via `registry.register()` at import time
- **Agent-level tools**: `todo`, `memory`, `session_search`, `delegate_task` intercepted before registry
- **Compression**: 50% threshold, protects last 20 messages, creates child session lineage
- **Prompt caching**: Anthropic `system_and_3` strategy (4 breakpoints)

## Delegation Patterns
- Spawn subagents via `delegate_task` tool with isolated context
- Monitor via `subagent_status`, steer via `subagent_steer`
- Aggregate via `synthesize_results` with conflict resolution
- Max 3 parallel subagents, 50 iterations each, depth limit 2

## Research Patterns
- `web_search` + `web_extract` for current info
- `arxiv_search` + `paper_analyze` for academic sources
- `source_validator` for credibility scoring
- `synthesize_results` for multi-source merging

## Planning Patterns
- `task_decompose` → hierarchical subtasks with dependencies
- `plan_create` → phased execution with parallel groups
- `plan_review` → feasibility, completeness, risk checks

## File Organization
- One file per tool in `tools/`
- One file per delegation component in `delegation/`
- Skills in `skills/<name>/SKILL.md`
- Tests mirror source structure in `tests/`

## Configuration
- `~/.enaya/config.yaml` for model/toolset/compression settings
- `~/.enaya/.env` for API keys
- Profile isolation via `enaya -p <name>`

## Testing
- Unit: tool handlers, auth, model parsing
- Integration: full agent loops, delegation flows
- Provider parity: all providers behave consistently
- Coverage gate: 60%