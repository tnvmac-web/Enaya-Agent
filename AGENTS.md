# AGENTS.md - Enaya Agent Development Guide

## Overview
Enaya Agent is a task-delegation AI agent built on Hermes Agent architecture principles. It specializes in multi-agent orchestration, deep research, structured planning, and result synthesis.

## Tech Stack
- **Core**: Python 3.11+, async/await, threading for interruptible operations
- **LLM Providers**: OpenRouter, Anthropic, OpenAI, NVIDIA, Google, Ollama, LM Studio (via shared runtime resolver)
- **Memory**: 5-layer (Session, Episodic, Semantic, Procedural, Project) with SQLite + ChromaDB
- **Tools**: 50+ built-in tools across 6 toolsets (core, research, planning, delegation, synthesis, codebase)
- **Interfaces**: CLI, ACP (VS Code/Zed/JetBrains), API Server (OpenAI-compatible), optional Gateway
- **Session Storage**: SQLite + FTS5 with lineage tracking
- **Context Compression**: LLM-based summarization at 50% threshold

## Project Structure
```
enaya-agent/
├── src/enaya/                      # Core package
│   ├── run_agent.py                # AIAgent facade (entry point)
│   ├── model_tools.py              # Tool schema collection & dispatch
│   ├── hermes_state.py             # SQLite session storage
│   ├── agent/                      # Agent loop & prompt system
│   │   ├── conversation_loop.py    # Main agent loop
│   │   ├── prompt_builder.py       # 3-tier prompt assembly
│   │   ├── context_compressor.py   # Default compression engine
│   │   ├── anthropic_adapter.py    # Anthropic Messages API
│   │   └── context_engine.py       # ContextEngine ABC
│   ├── cli/                        # CLI entry points
│   │   ├── main.py                 # Click CLI commands
│   │   ├── config.py               # Config loading (YAML + .env)
│   │   ├── auth.py                 # Provider registry & credentials
│   │   ├── models.py               # Model catalog & aliases
│   │   └── runtime_provider.py     # Runtime provider resolution
│   ├── tools/                      # Tool implementations
│   │   ├── registry.py             # Central tool registry
│   │   ├── file_tools.py           # read/write/patch/search
│   │   ├── web_tools.py            # web_search, web_extract
│   │   ├── delegation_tools.py     # delegate_task, subagent_*
│   │   ├── research_tools.py       # arxiv, paper_analyze, source_validator
│   │   ├── planning_tools.py       # task_decompose, plan_*
│   │   └── synthesis_tools.py      # synthesize, compare, extract
│   ├── delegation/                 # Multi-agent orchestration
│   │   ├── orchestrator.py         # Subagent lifecycle
│   │   ├── task_queue.py           # Priority queue
│   │   ├── result_aggregator.py    # Result synthesis
│   │   └── policies.py             # Delegation policies
│   ├── research/                   # Research pipeline
│   │   ├── web_researcher.py
│   │   ├── paper_analyzer.py
│   │   └── source_validator.py
│   ├── planning/                   # Planning engine
│   │   ├── task_decomposer.py
│   │   ├── plan_builder.py
│   │   └── plan_validator.py
│   ├── memory/                     # 5-layer memory
│   │   ├── five_layer.py
│   │   ├── semantic_store.py       # ChromaDB
│   │   └── project_indexer.py      # Codebase knowledge graph
│   ├── gateway/                    # Messaging gateway (optional)
│   ├── acp_adapter/                # ACP server
│   └── plugins/                    # Plugin system
├── skills/                         # Bundled skills
│   ├── enaya-research/
│   ├── enaya-planning/
│   ├── enaya-delegation/
│   ├── enaya-code-review/
│   └── enaya-doc-audit/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
├── pyproject.toml
├── README.md
├── AGENTS.md
├── HERMES.md
└── LICENSE
```

## Key Features Implemented

### 1. Delegation Engine
- **DelegationOrchestrator**: Subagent spawn/monitor/collect lifecycle
- **TaskQueue**: Priority-based with dependency resolution
- **ResultAggregator**: Deduplication, conflict detection, synthesis
- **Policies**: Complexity thresholds, domain routing, parallelization

### 2. Research Pipeline
- **WebResearcher**: Search → extract → validate → summarize
- **PaperAnalyzer**: arXiv/PDF ingestion → structured extraction
- **SourceValidator**: Credibility scoring, bias detection

### 3. Planning Engine
- **TaskDecomposer**: Hierarchical breakdown with dependencies
- **PlanBuilder**: Phased execution plans with parallel groups
- **PlanValidator**: Completeness, feasibility, risk checks

### 4. 5-Layer Memory
- **Session**: Current conversation (SQLite)
- **Episodic**: Specific events (SQLite)
- **Semantic**: General knowledge (ChromaDB vectors)
- **Procedural**: Skills/how-to (SQLite)
- **Project**: Codebase knowledge (codebase-memory-mcp)

## Development Workflow

### Local Development
```bash
cd enaya-agent
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e ".[dev]"
python -m pytest tests/ -n0 -q          # Full test suite
enaya chat -q "Hello, Enaya!"            # Smoke test
```

### Configuration
```yaml
# ~/.enaya/config.yaml (or profile-specific)
model: "openrouter:anthropic/claude-3.5-sonnet"
provider: "openrouter"
max_turns: 500
temperature: 0.7
toolsets: ["core", "research", "planning", "delegation", "synthesis"]
fallback_providers: []
compression_threshold: 0.50
```

### Environment Variables (.env)
```bash
OPENROUTER_API_KEY=sk-...
ANTHROPIC_TOKEN=sk-ant-...
OPENAI_API_KEY=sk-...
NVIDIA_API_KEY=...
GOOGLE_API_KEY=...
```

## Core Commands

| Command | Description |
|---------|-------------|
| `enaya chat -q "query"` | Run single query |
| `enaya chat` | Interactive mode |
| `enaya delegate "task"` | Delegate to subagent |
| `enaya research "query" --depth deep` | Deep research |
| `enaya plan "goal" --complexity moderate` | Create plan |
| `enaya model openrouter:anthropic/claude-3.5-sonnet` | Switch model |
| `enaya setup` | Interactive setup |
| `enaya acp` | Start ACP server |
| `enaya config --list` | Show config |

## Agent Loop Internals

### Turn Lifecycle
```
run_conversation()
  1. Append user message to history
  2. Build/reuse cached system prompt (3 tiers)
  3. Check preflight compression (>50% context)
  4. Build API messages from history
  5. Make interruptible API call
  6. Parse response:
     - tool_calls → execute → append results → loop
     - text → persist session → return
```

### API Modes
| Mode | Provider | Description |
|------|----------|-------------|
| `chat_completions` | OpenAI, OpenRouter, NVIDIA, etc. | Standard OpenAI format |
| `codex_responses` | OpenAI Codex | Responses API (stateful) |
| `anthropic_messages` | Anthropic (native) | Via anthropic_adapter.py |

### Message Format (OpenAI-compatible internally)
```python
{"role": "system", "content": "..."}
{"role": "user", "content": "..."}
{"role": "assistant", "content": "...", "tool_calls": [...]}
{"role": "tool", "tool_call_id": "...", "content": "..."}
```

### Tool Execution
- Single tool → direct in main thread
- Multiple tools → concurrent via ThreadPoolExecutor
- Interactive tools (clarify) → force sequential
- Results reinserted in original order

## Prompt Assembly (3 Tiers)

### Stable Tier (cached across turns)
1. Agent identity (SOUL.md or default)
2. Tool guidance (auto-generated from schemas)
3. Active skills descriptions

### Context Tier (loaded once per session)
- `.enaya.md` / `ENAYA.md` (walks to git root) — Priority 1
- `AGENTS.md` (CWD only) — Priority 2
- `CLAUDE.md` (CWD only) — Priority 3
- `.cursorrules` / `.cursor/rules/*.mdc` (CWD only) — Priority 4

### Volatile Tier (rebuilt each turn)
- Memory snapshots (MEMORY.md + USER.md)
- Profile data
- Timestamp
- Platform hints

## Context Compression

### Dual System
1. **Gateway Hygiene** (85%): Between turns, in-place, no LLM
2. **Agent Compressor** (50%): Preflight, LLM-based, creates child session

### Algorithm (4 Phases)
1. Prune old tool results (cheap)
2. Determine boundaries (head/tail/middle)
3. Generate structured summary (LLM call)
4. Assemble compressed messages

## Provider Resolution

### Precedence
1. Explicit CLI request (`--provider`, `--model`)
2. Config.yaml
3. Environment variables
4. Provider defaults

### Supported Providers (15+)
OpenRouter, OpenAI, Anthropic, NVIDIA, Google, Ollama, LM Studio, Custom

## Adding Tools

### Step 1: Create Tool File (`tools/<name>.py`)
```python
from enaya.tools.registry import registry

MY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "Specific description so model knows when to use",
        "parameters": {"type": "object", "properties": {...}, "required": [...]}
    }
}

def my_tool(arg: str) -> str:
    return json.dumps({"result": "..."})

registry.register(
    name="my_tool",
    toolset="my_toolset",
    schema=MY_TOOL_SCHEMA,
    handler=my_tool,
    check_fn=lambda: True,
)
```

### Step 2: Add to Toolset
Tool modules auto-discovered at import via `discover_builtin_tools()`.

### Key Rules
- Handler returns **JSON string** (not dict)
- Errors as `{"error": "..."}` JSON string
- Handler signature: `handler(args, **kwargs)` — always accept `**kwargs`
- Catch exceptions, return error JSON

## Adding Providers

### OpenAI-Compatible (Config Only)
1. Add to `auth.py` PROVIDER_REGISTRY
2. Add models to `models.py` _PROVIDER_MODELS
3. Add aliases to _PROVIDER_ALIASES
4. Wire in `runtime_provider.py` if needed
5. Update `auxiliary_client.py` and `model_metadata.py`

### Native Provider (Requires Adapter)
1. All above plus:
2. Create `agent/<provider>_adapter.py`
3. Update `run_agent.py` for new `api_mode`

## Plugin System

### Plugin Structure
```
my-plugin/
├── PLUGIN.yaml          # Manifest v2
├── tools/               # Tool schemas + handlers
├── hooks/               # Hook handlers
├── skills/              # Bundled skills
├── data/                # Data files
├── __init__.py          # register(ctx) function
└── pyproject.toml
```

### Registration
```python
def register(ctx: PluginContext):
    ctx.register_tool(name="my_tool", toolset="my_plugin", schema=..., handler=...)
    ctx.register_hook(event="agent:start", handler=...)
    ctx.register_skill(name="my_skill", skill_content=...)
```

## Session Storage

### Schema (SQLite + FTS5)
- `sessions`: id, profile, platform, chat_type, chat_id, created_at, parent_session_id, lineage_id
- `messages`: id, session_id, role, content, tool_call_id, display_kind, row_id, created_at
- `messages_fts`: FTS5 virtual table on content

### Lineage Tracking
Compression creates child session with new lineage_id, parent_session_id links to parent.

## Testing Strategy

```bash
# Full suite
pytest tests/ -n0 -q

# Targeted
pytest tests/agent/test_provider_parity.py -q
pytest tests/cli/test_runtime_provider_resolution.py -q
pytest tests/delegation/ -q

# Coverage gate
pytest --cov=enaya --cov-fail-under=60
```

## Key Files to Know

| File | Purpose |
|------|---------|
| `src/enaya/run_agent.py` | AIAgent facade |
| `src/enaya/agent/conversation_loop.py` | Core loop |
| `src/enaya/agent/prompt_builder.py` | Prompt assembly |
| `src/enaya/agent/context_compressor.py` | Compression |
| `src/enaya/tools/registry.py` | Tool registry |
| `src/enaya/model_tools.py` | Tool dispatch |
| `src/enaya/hermes_state.py` | Session storage |
| `src/enaya/cli/runtime_provider.py` | Provider resolution |
| `src/enaya/delegation/orchestrator.py` | Subagent orchestration |
| `src/enaya/delegation/policies.py` | Delegation logic |

## Architecture Diagrams

### Agent Loop
```
User Input → AIAgent.run_conversation() → Prompt Builder (3 tiers)
    → Runtime Provider → API Call (3 modes)
    → Tool Execute / Response Parse / Compress Check → Persist Session
```

### Delegation Flow
```
Task → DelegationOrchestrator → TaskQueue → Subagent (AIAgent)
    → monitor via subagent_status → steer if needed
    → collect results → ResultAggregator → synthesize
```

## Contributing

1. Follow Hermes Agent code style (type hints, docstrings, error handling)
2. Add tests for new functionality
3. Run full test suite: `pytest tests/ -n0 -q`
4. Update relevant documentation
5. PR to main branch

## References
- Hermes Agent Architecture: https://hermes-agent.nousresearch.com/docs/developer-guide/architecture
- Original Hermes repo: https://github.com/NousResearch/hermes-agent