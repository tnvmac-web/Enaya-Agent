# Enaya Agent — Comprehensive Documentation

> **Project**: Enaya Agent v0.1.0  
> **Type**: Task-delegation AI Agent (fork of Hermes Agent)  
> **Repository**: https://github.com/tnvmac-web/Enaya-Agent.git  
> **Author**: tnvmac  
> **License**: MIT  
> **Last Updated**: September 2026  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [Core Components](#4-core-components)
5. [Tool System](#5-tool-system)
6. [Delegation Engine](#6-delegation-engine)
7. [Research Pipeline](#7-research-pipeline)
8. [Planning Engine](#8-planning-engine)
9. [5-Layer Memory System](#9-5-layer-memory-system)
10. [Provider Resolution](#10-provider-resolution)
11. [CLI Interface](#11-cli-interface)
12. [Interfaces (TUI, API, ACP, Dashboard)](#12-interfaces)
13. [Plugin System](#13-plugin-system)
14. [Gateway & Messaging Platforms](#14-gateway--messaging-platforms)
15. [Configuration](#15-configuration)
16. [Session Storage](#16-session-storage)
17. [Context Compression](#17-context-compression)
18. [Prompt Assembly](#18-prompt-assembly)
19. [Testing Strategy](#19-testing-strategy)
20. [Development Workflow](#20-development-workflow)
21. [Implementation Roadmap](#21-implementation-roadmap)
22. [Key Files Reference](#22-key-files-reference)
23. [Dependencies](#23-dependencies)
24. [Risk Assessment](#24-risk-assessment)

---

## 1. Project Overview

**Enaya Agent** is a task-delegation AI agent built on Hermes Agent architecture principles. It specializes in multi-agent orchestration, deep research, structured planning, and result synthesis. The core philosophy is **"Delegate, Research, Execute"** — breaking down complex tasks, delegating to specialized subagents, and synthesizing results.

### Key Differentiators from Hermes
- **Delegation-first design**: Native subagent orchestration with budgets, policies, and result aggregation
- **Research pipeline**: Built-in web search, academic paper analysis, and source validation
- **Planning engine**: Hierarchical task decomposition with feasibility checking
- **Synthesis tools**: Multi-source result merging and claim extraction
- **Profile isolation**: Multiple concurrent instances via `enaya -p <name>`

### Design Principles
- **Platform-Agnostic Core**: One `AIAgent` serves CLI, gateway, ACP, API server
- **Observable Execution**: Every tool call visible via callbacks
- **Interruptible**: API calls and tools cancellable mid-flight
- **Loose Coupling**: Optional subsystems use registry patterns
- **Profile Isolation**: Multiple concurrent instances via profile system

---

## 2. Architecture

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────────┐
│                        Enaya Agent                                    │
├─────────────────────────────────────────────────────────────────────┤
│  AIAgent (run_agent.py) — Single class, all entry points        │
├─────────────────────────────────────────────────────────────────────┤
│  Agent Loop    │  Prompt System     │  Provider Resolver          │
│  conversation   │  prompt_builder     │  runtime_provider          │
│  context_comp   │  anthropic_adapter  │  models.py                 │
├─────────────────────────────────────────────────────────────────────┤
│  Tools (50+)      │  Delegation         │  Memory               │
│  registry          │  orchestrator       │  5-layer (SQLite+Chroma)│
│  file/web/research │  task_queue         │  project_indexer      │
│  planning/synthesis│  result_aggregator  │  semantic_store       │
├─────────────────────────────────────────────────────────────────────┤
│  Interfaces: CLI • TUI • ACP (VS Code/Zed) • API Server • Dashboard │
├─────────────────────────────────────────────────────────────────────┤
│  Gateway: Telegram • Discord • Slack • Matrix • Email • (more)      │
├─────────────────────────────────────────────────────────────────────┤
│  Plugins: Model Providers • Platforms • Memory • Custom             │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Loop (Turn Lifecycle)
```
User Input → AIAgent.run_conversation() → Prompt Builder (3 tiers)
    → Runtime Provider → API Call (3 modes)
    → Tool Execute / Response Parse / Compress Check → Persist Session
```

1. **Append user message** to conversation history
2. **Build/reuse cached system prompt** (3 tiers: Stable, Context, Volatile)
3. **Check preflight compression** (>50% context threshold)
4. **Build API messages** from conversation history
5. **Make interruptible API call**
6. **Parse response**:
   - `tool_calls` → execute → append results → loop
   - `text` → persist session → return

### Delegation Flow
```
Task → DelegationOrchestrator → TaskQueue → Subagent (AIAgent)
    → monitor via subagent_status → steer if needed
    → collect results → ResultAggregator → synthesize
```

### Message Format (OpenAI-compatible internally)
```python
{"role": "system", "content": "..."}
{"role": "user", "content": "..."}
{"role": "assistant", "content": "...", "tool_calls": [...]}
{"role": "tool", "tool_call_id": "...", "content": "..."}
```

### API Modes
| Mode | Provider | Description |
|------|----------|-------------|
| `chat_completions` | OpenAI, OpenRouter, NVIDIA, etc. | Standard OpenAI format |
| `codex_responses` | OpenAI Codex | Responses API (stateful) |
| `anthropic_messages` | Anthropic (native) | Via anthropic_adapter.py |

---

## 3. Project Structure

```
enaya-agent/
├── src/enaya/                      # Core package
│   ├── __init__.py
│   ├── run_agent.py                # AIAgent facade (entry point)
│   ├── model_tools.py              # Tool schema collection & dispatch
│   ├── hermes_state.py             # SQLite session storage
│   ├── agent/                      # Agent loop & prompt system
│   │   ├── __init__.py
│   │   ├── conversation_loop.py    # Main agent loop
│   │   ├── prompt_builder.py       # 3-tier prompt assembly
│   │   ├── context_compressor.py   # Default compression engine
│   │   ├── anthropic_adapter.py    # Anthropic Messages API
│   │   └── context_engine.py       # ContextEngine ABC
│   ├── cli/                        # CLI entry points
│   │   ├── __init__.py
│   │   ├── main.py                 # Click CLI commands
│   │   ├── config.py               # Config loading (YAML + .env)
│   │   ├── auth.py                 # Provider registry & credentials
│   │   ├── models.py               # Model catalog & aliases
│   │   └── runtime_provider.py     # Runtime provider resolution
│   ├── tools/                      # Tool implementations
│   │   ├── __init__.py
│   │   ├── registry.py             # Central tool registry
│   │   ├── file_tools.py           # read/write/patch/search
│   │   ├── web_tools.py            # web_search, web_extract
│   │   ├── delegation_tools.py     # delegate_task, subagent_*
│   │   ├── research_tools.py       # arxiv, paper_analyze, source_validator
│   │   ├── planning_tools.py       # task_decompose, plan_*
│   │   ├── synthesis_tools.py      # synthesize, compare, extract
│   │   ├── terminal_tool.py        # terminal execution
│   │   ├── code_execution_tool.py  # sandboxed code execution
│   │   ├── browser_cdp_tool.py     # browser CDP control
│   │   ├── process_tool.py         # process management
│   │   └── voice_tool.py           # voice integration
│   ├── delegation/                 # Multi-agent orchestration
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Subagent lifecycle
│   │   ├── task_queue.py           # Priority queue
│   │   ├── result_aggregator.py    # Result synthesis
│   │   └── policies.py             # Delegation policies
│   ├── research/                   # Research pipeline
│   │   ├── __init__.py
│   │   ├── web_researcher.py       # Search → extract → validate → summarize
│   │   ├── paper_analyzer.py       # arXiv/PDF ingestion
│   │   └── source_validator.py     # Credibility scoring, bias detection
│   ├── planning/                   # Planning engine
│   │   ├── __init__.py
│   │   ├── task_decomposer.py      # Hierarchical breakdown
│   │   ├── plan_builder.py         # Phased execution plans
│   │   └── plan_validator.py       # Completeness, feasibility checks
│   ├── memory/                     # 5-layer memory
│   │   ├── __init__.py
│   │   ├── five_layer.py           # 5-layer memory implementation
│   │   ├── semantic_store.py       # ChromaDB vectors
│   │   └── project_indexer.py      # Codebase knowledge graph
│   ├── gateway/                    # Messaging gateway (optional)
│   │   ├── __init__.py
│   │   ├── runner.py               # Gateway message dispatch
│   │   └── platforms/              # Platform adapters
│   │       ├── __init__.py
│   │       ├── telegram.py
│   │       ├── discord.py
│   │       ├── slack.py
│   │       ├── matrix.py
│   │       ├── email.py
│   │       ├── signal.py
│   │       └── whatsapp.py
│   ├── acp_adapter/                # ACP server (VS Code/Zed/JetBrains)
│   ├── plugins/                    # Plugin system
│   │   ├── __init__.py
│   │   ├── model-providers/
│   │   ├── platforms/
│   │   └── memory/
│   ├── cli/                        # CLI commands (see above)
│   ├── tui/                        # Textual TUI interface
│   │   ├── main.py
│   ├── dashboard/                  # Web dashboard
│   │   ├── server.py
│   │   └── index.html
│   ├── voice/                      # Voice mode
│   │   ├── manager.py
│   ├── browser/                    # Browser automation
│   │   ├── manager.py
│   ├── vision/                     # Vision/multimodal
│   │   ├── manager.py
│   ├── image_gen/                  # Image generation (FAL.ai)
│   │   ├── manager.py
│   ├── cron/                       # Cron jobs
│   │   ├── manager.py
│   ├── kanban/                     # Kanban task board
│   │   ├── manager.py
│   ├── hooks/                      # Lifecycle hooks
│   │   ├── manager.py
│   ├── pets/                       # Animated mascots
│   │   ├── manager.py
│   ├── themes/                     # Theme/skin system
│   │   ├── manager.py
│   ├── mcp/                        # MCP client
│   │   ├── client.py
│   ├── research/                   # Research pipeline (see above)
│   └── delegation/                 # Delegation engine (see above)
├── skills/                         # Bundled skills
│   ├── enaya-research/SKILL.md
│   ├── enaya-planning/SKILL.md
│   ├── enaya-delegation/SKILL.md
│   ├── enaya-code-review/SKILL.md
│   └── enaya-doc-audit/SKILL.md
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
├── pyproject.toml
├── README.md
├── AGENTS.md
├── HERMES.md
├── DEVELOPMENT_PLAN.md
├── IMPLEMENTATION_PLAN.md
└── LICENSE
```

---

## 4. Core Components

### 4.1 AIAgent Facade (`run_agent.py`)

The `AIAgent` class is the central entry point — one class serves all interfaces (CLI, gateway, ACP, API server, batch). Platform differences live in entry points, not the agent core.

**Key attributes:**
- `config: AgentConfig` — All configuration (model, provider, toolsets, limits)
- `conversation_history: list[dict]` — Message history
- `session_store: SessionStore` — SQLite persistence
- `registry: ToolRegistry` — Central tool registry
- `orchestrator: DelegationOrchestrator` — Subagent management

**Callback system:**
- `ToolProgressCallback` — tool_name, status, is_start
- `ThinkingCallback` — is_thinking
- `ReasoningCallback` — reasoning_content
- `ClarifyCallback` — question, choices → answer
- `StreamDeltaCallback` — delta chunks
- `StepCallback` — step_info
- `StatusCallback` — status_message

**AgentConfig dataclass:**
```python
@dataclass
class AgentConfig:
    model: str = "openrouter:anthropic/claude-sonnet-4"
    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    api_mode: str = "chat_completions"
    max_turns: int = 500
    temperature: float = 0.7
    top_p: float = 1.0
    system_prompt: str | None = None
    fallback_providers: list[tuple[str, str]] = field(default_factory=list)
    toolsets: list[str] = field(default_factory=lambda: ["core"])
    disabled_tools: list[str] = field(default_factory=list)
    compression_threshold: float = 0.50
    compression_protect_last_n: int = 20
    prompt_caching: bool = True
    prompt_caching_ttl: str = "5m"
    session_id: str | None = None
    profile: str = "default"
    platform: str = "cli"
```

### 4.2 Conversation Loop (`agent/conversation_loop.py`)

The `run_conversation()` function implements the main agent loop with turn phases:

```python
def run_conversation(agent, user_input, *, prefill, ephemeral_system_prompt) -> str:
    # 1. Append user message to history
    # 2. Build or reuse cached system prompt
    # 3. Check preflight compression
    # 4. Build API messages
    # 5. Main loop (max_turns iterations):
    #    a. Check interruption
    #    b. Make interruptible API call
    #    c. Parse response (tool_calls → execute, text → return)
    #    d. Persist session
```

**Key behaviors:**
- Single tool → direct in main thread
- Multiple tools → concurrent via `ThreadPoolExecutor`
- Interactive tools (clarify) → force sequential
- Results reinserted in original order

### 4.3 Prompt Builder (`agent/prompt_builder.py`)

3-tier prompt assembly with caching:

**Stable Tier** (cached across turns):
1. Agent identity (SOUL.md or default)
2. Tool guidance (auto-generated from schemas)
3. Active skills descriptions

**Context Tier** (loaded once per session):
1. `.enaya.md` / `ENAYA.md` (walks to git root) — Priority 1
2. `AGENTS.md` (CWD only) — Priority 2
3. `CLAUDE.md` (CWD only) — Priority 3
4. `.cursorrules` / `.cursor/rules/*.mdc` (CWD only) — Priority 4

**Volatile Tier** (rebuilt each turn):
1. Memory snapshots (MEMORY.md + USER.md)
2. Profile data
3. Timestamp
4. Platform hints

### 4.4 Context Compressor (`agent/context_compressor.py`)

Dual compression system:
1. **Gateway Hygiene** (85%): Between turns, in-place, no LLM
2. **Agent Compressor** (50%): Preflight, LLM-based, creates child session

**4-Phase Algorithm:**
1. Prune old tool results (cheap)
2. Determine boundaries (head/tail/middle)
3. Generate structured summary (LLM call)
4. Assemble compressed messages

**Parameters:**
- 50% threshold triggers compression
- Protects last 20 messages
- Creates child session with lineage tracking
- Max 3 attempts

---

## 5. Tool System

### 5.1 Tool Registry (`tools/registry.py`)

Central registry with auto-discovery via `discover_builtin_tools()` at import time. Tools are registered using:

```python
from enaya.tools.registry import registry

registry.register(
    name="my_tool",
    toolset="my_toolset",
    schema=MY_TOOL_SCHEMA,
    handler=my_tool,
    check_fn=lambda: True,
)
```

**Key Rules:**
- Handler returns **JSON string** (not dict)
- Errors as `{"error": "..."}` JSON string
- Handler signature: `handler(args, **kwargs)` — always accept `**kwargs`
- Catch exceptions, return error JSON

### 5.2 Toolsets

| Toolset | Tools | Purpose |
|---------|-------|---------|
| **core** | `read_file`, `write_file`, `patch`, `terminal`, `web_search`, `web_extract`, `clarify`, `todo`, `memory`, `session_search`, `delegate_task` | Core agent operations |
| **research** | `arxiv_search`, `paper_analyze`, `source_validator`, `web_research` | Deep research |
| **planning** | `task_decompose`, `plan_create`, `plan_update`, `plan_review` | Structured planning |
| **delegation** | `delegate_task`, `subagent_status`, `subagent_steer`, `subagent_stop` | Multi-agent orchestration |
| **synthesis** | `synthesize_results`, `compare_sources`, `extract_claims` | Result aggregation |
| **codebase** | `code_search`, `code_analyze`, `code_modify`, `test_run` | Codebase interaction |
| **terminal** | `terminal`, `process_info` | Terminal/process management |
| **file** | `read_file`, `write_file`, `patch`, `search_files`, `list_directory` | File operations |
| **browser** | `navigate`, `screenshot`, `click`, `type_text`, `extract_content` | Browser CDP |
| **voice** | `speak`, `listen`, `transcribe` | Voice integration |
| **image_gen** | `generate_image` | Image generation (FAL.ai) |

### 5.3 Tool Files Organization

Each tool is in its own file under `src/enaya/tools/`:
- `file_tools.py` — read/write/patch/search operations
- `web_tools.py` — web_search, web_extract
- `delegation_tools.py` — delegate_task, subagent_*
- `research_tools.py` — arxiv, paper_analyze, source_validator
- `planning_tools.py` — task_decompose, plan_*
- `synthesis_tools.py` — synthesize, compare, extract
- `terminal_tool.py` — terminal execution
- `code_execution_tool.py` — sandboxed code execution
- `browser_cdp_tool.py` — browser CDP control
- `process_tool.py` — process management
- `voice_tool.py` — voice integration
- `registry.py` — Central tool registry

---

## 6. Delegation Engine

### 6.1 DelegationOrchestrator (`delegation/orchestrator.py`)

Manages subagent lifecycle: spawn, monitor, collect results, synthesize.

```python
class DelegationOrchestrator:
    def __init__(self, parent_agent: AIAgent):
        self.parent_agent = parent_agent
        self.subagents: dict[str, SubagentTask] = {}
        self.task_queue: list[str] = []
        self.max_parallel = 3
        self._running_count = 0

    def delegate(self, task, context, model, max_iterations, toolsets) → str  # task_id
    def monitor(self, task_id) → SubagentStatus
    def steer(self, task_id, message)
    def stop(self, task_id)
    def collect_results(self) → list[SubagentTask]
```

**SubagentTask dataclass:**
```python
@dataclass
class SubagentTask:
    id: str
    task: str
    context: str
    model: str
    max_iterations: int
    toolsets: list[str]
    status: SubagentStatus  # PENDING, RUNNING, COMPLETED, FAILED, STOPPED
    result: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    steer_messages: list[str]
```

**Constraints:**
- Max 3 parallel subagents
- 50 iterations each
- Depth limit 2

### 6.2 TaskQueue (`delegation/task_queue.py`)

Priority-based queue with dependency resolution.

### 6.3 ResultAggregator (`delegation/result_aggregator.py`)

Deduplication, conflict detection, synthesis.

### 6.4 Policies (`delegation/policies.py`)

Delegation policies: complexity thresholds, domain routing, parallelization limits.

---

## 7. Research Pipeline

### 7.1 WebResearcher (`research/web_researcher.py`)

Pipeline: Search → Extract → Validate → Summarize.

### 7.2 PaperAnalyzer (`research/paper_analyzer.py`)

arXiv/PDF ingestion → structured extraction.

### 7.3 SourceValidator (`research/source_validator.py`)

Credibility scoring, bias detection.

### 7.4 Research Tools

| Tool | Function |
|------|----------|
| `web_search` | Search the web |
| `web_extract` | Extract content from URLs |
| `arxiv_search` | Search arXiv papers |
| `paper_analyze` | Analyze academic papers |
| `source_validator` | Credibility scoring |
| `web_research` | Full research pipeline |

---

## 8. Planning Engine

### 8.1 TaskDecomposer (`planning/task_decomposer.py`)

Hierarchical task breakdown with dependencies.

### 8.2 PlanBuilder (`planning/plan_builder.py`)

Phased execution plans with parallel groups.

### 8.3 PlanValidator (`planning/plan_validator.py`)

Completeness, feasibility, risk checks.

### 8.4 Planning Tools

| Tool | Function |
|------|----------|
| `task_decompose` | Break task into subtasks |
| `plan_create` | Create structured plan |
| `plan_update` | Update existing plan |
| `plan_review` | Validate plan quality |

---

## 9. 5-Layer Memory System

### 9.1 Architecture

Each layer has its own SQLite database:

```python
class FiveLayerMemory:
    """
    1. Session - Current conversation context (SQLite)
    2. Episodic - Specific events/interactions (SQLite)
    3. Semantic - General knowledge/facts (ChromaDB vectors)
    4. Procedural - Skills/how-to knowledge (SQLite)
    5. Project - Codebase/project-specific knowledge (ChromaDB)
    """
```

### 9.2 Layer Details

| Layer | Storage | Purpose | Access Pattern |
|-------|---------|---------|----------------|
| **Session** | SQLite | Current conversation context | Ephemeral, cleared at end |
| **Episodic** | SQLite | Specific events/interactions | Append-only, time-based |
| **Semantic** | ChromaDB | General knowledge/facts | Vector similarity search |
| **Procedural** | SQLite | Skills/how-to knowledge | Keyword lookup |
| **Project** | ChromaDB | Codebase knowledge | Codebase-memory-mcp integration |

### 9.3 MemoryEntry Dataclass

```python
@dataclass
class MemoryEntry:
    id: str
    layer: str  # session, episodic, semantic, procedural, project
    content: str
    tags: list[str]
    importance: float = 1.0  # 0-1
    created_at: datetime
    updated_at: datetime
    access_count: int = 0
    source: str = ""
```

### 9.4 Project Indexer

`memory/project_indexer.py` integrates with codebase-memory-mcp for codebase knowledge graph.

---

## 10. Provider Resolution

### 10.1 Resolution Precedence
1. Explicit CLI request (`--provider`, `--model`)
2. Config.yaml
3. Environment variables
4. Provider defaults

### 10.2 Supported Providers (15+)

| Provider | Models | API Mode |
|----------|--------|----------|
| **OpenRouter** | Claude, GPT, Gemini, Llama, Nemotron | `chat_completions` |
| **Anthropic** | Claude 3.5 Sonnet/Haiku/Opus | `anthropic_messages` |
| **OpenAI** | GPT-4o, GPT-4o-mini, o1 | `chat_completions` |
| **NVIDIA** | Nemotron 3 Ultra, Llama 3.1 | `chat_completions` |
| **Google** | Gemini 1.5 Pro/Flash | `chat_completions` |
| **Ollama** | Local models | `chat_completions` |
| **LM Studio** | Local models | `chat_completions` |
| **Custom** | Any OpenAI-compatible | `chat_completions` |

### 10.3 Configuration

**config.yaml** (at `~/.enaya/config.yaml`):
```yaml
model:
  default: nvidia/nemotron-3-ultra-550b-a55b
  provider: nvidia
  base_url: https://integrate.api.nvidia.com/v1
  key_env: HERMES_CUSTOM_HPC_AI_API_KEY
```

**CLI usage:**
```bash
enaya model openrouter:anthropic/claude-3.5-sonnet
enaya chat -q "Hello" --provider openrouter --model openrouter:anthropic/claude-sonnet-4
```

### 10.4 Runtime Provider Resolution (`cli/runtime_provider.py`)

`resolve_runtime_provider()` handles the full resolution chain including fallback providers and base URL overrides.

---

## 11. CLI Interface

### 11.1 Commands

| Command | Description |
|---------|-------------|
| `enaya chat -q "query"` | Run single query |
| `enaya chat` | Interactive mode |
| `enaya delegate "task"` | Delegate to subagent |
| `enaya research "query" --depth deep` | Deep research |
| `enaya plan "goal" --complexity moderate` | Create plan |
| `enaya model openrouter:anthropic/claude-3.5-sonnet` | Switch model |
| `enaya setup` | Interactive setup wizard |
| `enaya acp` | Start ACP server |
| `enaya tui` | Start TUI interface |
| `enaya dashboard` | Start web dashboard |
| `enaya api-server` | Start API server |
| `enaya config --list` | Show config |
| `enaya -p <profile>` | Use specific profile |

### 11.2 CLI Architecture

Built with **Click** framework:
- Main group: `cli()` with `--profile` option
- All commands share the same `AIAgent` instance
- Profile isolation via `ENAYA_HOME` environment variable
- `~/.enaya/profiles/<name>/` for non-default profiles

### 11.3 Setup Wizard

`enaya setup` guides through:
1. Provider selection
2. API key configuration
3. Default model selection
4. Toolset configuration
5. Profile creation

---

## 12. Interfaces

### 12.1 TUI (Textual)

Interactive terminal UI with:
- Mouse support
- Non-blocking input, rich overlays
- Session list, streaming tool output
- Widget apps (ticker, clock, dashboard)
- Command palette (Cmd+K)
- Command: `enaya tui`
- Optional dep: `textual>=0.70`

### 12.2 API Server (OpenAI-Compatible)

FastAPI server with streaming SSE:
- `POST /v1/chat/completions` (streaming)
- `POST /v1/responses` (stateful)
- `POST /v1/runs` / `GET /v1/runs/{id}`
- `POST /v1/runs/{id}/approval` / `steer` / `stop`
- `GET /v1/capabilities`
- `GET /v1/models`
- Command: `enaya api-server`
- Optional dep: `fastapi>=0.100`, `uvicorn>=0.23`

### 12.3 ACP Server (Agent Context Protocol)

JSON-RPC over stdio for VS Code/Zed/JetBrains:
- Session creation, prompt submission
- Streaming chunks, tool-call events
- Permission requests, session fork, cancel
- Command: `enaya acp`
- Binary: `bin/hermes-acp.exe`

### 12.4 Web Dashboard

Features:
- Embedded chat interface
- Configuration management
- MCP server catalog
- Messaging platform pairing
- Memory browser
- Profile builder
- OAuth/token authentication gate
- Command: `enaya dashboard`
- Optional dep: `fastapi>=0.100`, `uvicorn>=0.23`, `websockets>=11`

---

## 13. Plugin System

### 13.1 Plugin Structure

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

### 13.2 Registration

```python
def register(ctx: PluginContext):
    ctx.register_tool(name="my_tool", toolset="my_plugin", schema=..., handler=...)
    ctx.register_hook(event="agent:start", handler=...)
    ctx.register_skill(name="my_skill", skill_content=...)
```

### 13.3 Plugin Sources
1. **Bundled** — Built-in plugins in `src/enaya/plugins/`
2. **User** — `~/.enaya/plugins/`
3. **Project** — `.enaya/plugins/`

### 13.4 Existing Plugins
- `plugins/model-providers/` — LLM provider adapters
- `plugins/platforms/` — Messaging platform adapters
- `plugins/memory/` — Memory backend implementations

---

## 14. Gateway & Messaging Platforms

### 14.1 Gateway Core (`gateway/runner.py`)

Features:
- Message dispatch and routing
- Session persistence
- Reply, cron, home channel, cross-platform delivery
- Authorization (allowlists, DM pairing)
- Slash command dispatch
- Hook system (gateway:startup, session:*, agent:*, command:*)
- Cron ticking
- Token locks, profile-scoped process tracking

### 14.2 Platform Adapters

| Platform | Module | Status |
|----------|--------|--------|
| **Telegram** | `gateway/platforms/telegram.py` | ✅ Implemented |
| **Discord** | `gateway/platforms/discord.py` | ✅ Implemented |
| **Slack** | `gateway/platforms/slack.py` | ✅ Implemented |
| **Matrix** | `gateway/platforms/matrix.py` | ✅ Implemented |
| **Email** | `gateway/platforms/email.py` | ✅ Implemented |
| **Signal** | `gateway/platforms/signal.py` | ✅ Implemented |
| **WhatsApp** | `gateway/platforms/whatsapp.py` | ✅ Implemented |

### 14.3 Gateway Commands
```bash
enaya gateway start    # Start gateway
enaya gateway status   # Check gateway status
```

---

## 15. Configuration

### 15.1 Config File (`~/.enaya/config.yaml`)

```yaml
model:
  default: openrouter:anthropic/claude-3.5-sonnet
  provider: openrouter
max_turns: 500
temperature: 0.7
toolsets: ["core", "research", "planning", "delegation", "synthesis"]
fallback_providers: []
compression_threshold: 0.50
compression_protect_last_n: 20
prompt_caching: true
prompt_caching_ttl: "5m"
agent_identity: "enaya"
```

### 15.2 Environment Variables (`~/.enaya/.env`)

```bash
OPENROUTER_API_KEY=sk-...
ANTHROPIC_TOKEN=sk-ant-...
OPENAI_API_KEY=sk-...
NVIDIA_API_KEY=...
GOOGLE_API_KEY=...
GEMINI_API_KEY=...
OLLAMA_HOST=http://localhost:11434
LMSTUDIO_HOST=http://localhost:1234
```

### 15.3 Optional Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `ANTHROPIC_TOKEN` | Anthropic API token (or `CLAUDE_CODE_OAUTH_TOKEN`) |
| `OPENAI_API_KEY` | OpenAI API key |
| `NVIDIA_API_KEY` | NVIDIA NIM API key |
| `GOOGLE_API_KEY` | Google/Gemini API key |
| `OLLAMA_HOST` | Ollama host (default: http://localhost:11434) |
| `LMSTUDIO_HOST` | LM Studio host (default: http://localhost:1234) |
| `CUSTOM_API_KEY` | Custom OpenAI-compatible API key |
| `CUSTOM_BASE_URL` | Custom OpenAI-compatible base URL |

### 15.4 Profile Isolation

Each profile has its own directory:
- Default: `~/.enaya/`
- Named: `~/.enaya/profiles/<name>/`
- Environment variable: `ENAYA_HOME`
- CLI: `enaya -p <name>`

---

## 16. Session Storage

### 16.1 Schema (SQLite + FTS5)

**Tables:**
- `sessions`: id, profile, platform, chat_type, chat_id, created_at, parent_session_id, lineage_id
- `messages`: id, session_id, role, content, tool_call_id, display_kind, row_id, created_at
- `messages_fts`: FTS5 virtual table on content

### 16.2 Lineage Tracking

Compression creates child session with new `lineage_id`, `parent_session_id` links to parent. This enables:
- Full conversation history reconstruction
- Context compression audit trail
- Session branching/forking

### 16.3 SessionStore (`hermes_state.py`)

Full-featured state management:
- Session CRUD operations
- Message append/retrieve
- FTS5 full-text search
- Lineage tracking
- Gateway state management
- Usage tracking
- Session rewind/checkpoint

---

## 17. Context Compression

### 17.1 Dual System

1. **Gateway Hygiene** (85%): Between turns, in-place, no LLM
2. **Agent Compressor** (50%): Preflight, LLM-based, creates child session

### 17.2 Compression Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `threshold` | 0.5 | 50% context usage triggers compression |
| `target_ratio` | 0.2 | Compress to 20% of original |
| `protect_last_n` | 20 | Never compress last 20 messages |
| `protect_first_n` | 3 | Never compress first 3 messages |
| `max_attempts` | 3 | Max compression attempts per turn |
| `codex_gpt55_autoraise` | true | Auto-raise for GPT-5.5 |
| `idle_compact_after_seconds` | 0 | Idle compression trigger |
| `proactive_prune_tokens` | 0 | Proactive pruning token budget |
| `proactive_prune_min_reclaim_tokens` | 4096 | Min tokens to reclaim |

### 17.3 Compression Algorithm (4 Phases)

1. **Prune** old tool results (cheap, no LLM)
2. **Determine boundaries** (head/tail/middle split)
3. **Generate structured summary** (LLM call)
4. **Assemble compressed messages** (head + summary + tail)

---

## 18. Prompt Assembly

### 18.1 Three Tiers

**Stable Tier** (cached across turns):
1. Agent identity (SOUL.md or default)
2. Tool guidance (auto-generated from schemas)
3. Active skills descriptions

**Context Tier** (loaded once per session):
1. `.enaya.md` / `ENAYA.md` (walks to git root) — Priority 1
2. `AGENTS.md` (CWD only) — Priority 2
3. `CLAUDE.md` (CWD only) — Priority 3
4. `.cursorrules` / `.cursor/rules/*.mdc` (CWD only) — Priority 4

**Volatile Tier** (rebuilt each turn):
1. Memory snapshots (MEMORY.md + USER.md)
2. Profile data
3. Timestamp
4. Platform hints

### 18.2 Prompt Caching

- Anthropic `system_and_3` strategy (4 breakpoints)
- TTL: 5 minutes
- Enabled by default (`prompt_caching: true`)

---

## 19. Testing Strategy

### 19.1 Test Levels

| Level | Coverage | Tools |
|-------|----------|-------|
| Unit | ≥90% | pytest, pytest-asyncio |
| Integration | ≥80% | Full agent loops, delegation flows |
| E2E | Key paths | Real delegation scenarios |
| Provider Parity | All providers | `test_provider_parity.py` pattern |

### 19.2 Test Commands

```bash
# Full suite
pytest tests/ -n0 -q

# Targeted
pytest tests/agent/test_provider_parity.py -q
pytest tests/cli/test_runtime_provider_resolution.py -q
pytest tests/delegation/ -q

# Coverage gate
pytest --cov=enaya --cov-fail-under=60

# Lint
ruff check src/

# Type check
mypy src/enaya/
```

### 19.3 Current Test Status

- **11 unit tests passing** (as of latest commit)
- Coverage gate: 60% (configured in `pyproject.toml`)
- Test paths: `tests/unit/`, `tests/integration/`, `tests/e2e/`

---

## 20. Development Workflow

### 20.1 Setup

```bash
# Clone
git clone https://github.com/tnvmac-web/Enaya-Agent.git
cd enaya-agent

# Create venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install
pip install -e ".[dev]"

# Run smoke test
enaya chat -q "Hello, Enaya!"
```

### 20.2 Adding Tools

1. Create `tools/<name>.py` with schema + handler
2. Register via `registry.register()` at import time
3. Handler returns JSON string, not dict
4. Auto-discovered via `discover_builtin_tools()`

### 20.3 Adding Providers

**OpenAI-Compatible** (Config Only):
1. Add to `auth.py` PROVIDER_REGISTRY
2. Add models to `models.py` _PROVIDER_MODELS
3. Add aliases to _PROVIDER_ALIASES
4. Wire in `runtime_provider.py`

**Native Provider** (Requires Adapter):
1. All above plus:
2. Create `agent/<provider>_adapter.py`
3. Update `run_agent.py` for new `api_mode`

### 20.4 Code Style

- Type hints on all public functions
- Error handling: Catch exceptions, return JSON error strings
- Tool registration: Auto-discovery via `registry.register()`
- Ruff line-length: 100
- Mypy strict mode for type checking

---

## 21. Implementation Roadmap

### Phase 1: Core Interfaces (Completed)
- ✅ TUI (Textual)
- ✅ API Server (FastAPI)
- ✅ ACP Server (JSON-RPC stdio)
- ✅ Web Dashboard
- ✅ CLI commands (tui, dashboard, api_server, acp)

### Phase 2: Messaging Gateway (Completed)
- ✅ Gateway Core
- ✅ Platform Adapters: Telegram, Discord, Slack, Matrix, Email
- ✅ WhatsApp, Signal

### Phase 3: Media & AI Features (Completed)
- ✅ Voice Mode (STT/TTS)
- ✅ Browser Automation (CDP)
- ✅ Vision (Multimodal)
- ✅ Image Generation (FAL.ai)

### Phase 4: Extensibility (Completed)
- ✅ Plugin System
- ✅ Themes/Skins
- ✅ Pets (Mascots)
- ✅ MCP Support

### Phase 5: Automation & Orchestration
- 🔄 Cron Jobs
- 🔄 Kanban
- 🔄 Hooks
- 🔄 Batch Processing

### Phase 6: Platform & Distribution
- 📋 Windows Installer (NSIS)
- 📋 CI/CD Pipeline
- 📋 Desktop App (Electron/Tauri)

### Phase 7: Advanced Features
- 📋 Profiles Enhancement
- 📋 Context Files
- 📋 Security Features
- 📋 Import from Other Agents

---

## 22. Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `src/enaya/run_agent.py` | 588 | AIAgent facade — all entry points |
| `src/enaya/agent/conversation_loop.py` | 242 | Main agent loop |
| `src/enaya/agent/prompt_builder.py` | — | 3-tier prompt assembly |
| `src/enaya/agent/context_compressor.py` | — | Context compression engine |
| `src/enaya/tools/registry.py` | — | Central tool registry |
| `src/enaya/model_tools.py` | — | Tool dispatch |
| `src/enaya/hermes_state.py` | — | SQLite session storage |
| `src/enaya/cli/main.py` | 678 | Click CLI commands |
| `src/enaya/cli/config.py` | 153 | Config loading, defaults |
| `src/enaya/cli/runtime_provider.py` | — | Provider resolution |
| `src/enaya/delegation/orchestrator.py` | 241 | Subagent lifecycle |
| `src/enaya/delegation/policies.py` | — | Delegation policies |
| `src/enaya/memory/five_layer.py` | 220 | 5-layer memory system |
| `src/enaya/memory/semantic_store.py` | — | ChromaDB integration |
| `src/enaya/research/web_researcher.py` | — | Research pipeline |
| `src/enaya/planning/task_decomposer.py` | — | Task decomposition |
| `src/enaya/gateway/runner.py` | — | Gateway message dispatch |
| `src/enaya/cli/auth.py` | — | Provider registry & credentials |
| `src/enaya/cli/models.py` | — | Model catalog & aliases |
| `pyproject.toml` | 137 | Project configuration, dependencies |

---

## 23. Dependencies

### Core Runtime
```
pydantic>=2.7          # Data validation and settings
pyyaml>=6.0            # YAML configuration
rich>=13.7             # Rich terminal output
click>=8.1             # CLI framework
chromadb>=0.5          # Vector database for semantic memory
networkx>=3.2          # Graph algorithms (knowledge graph)
watchdog>=3.0          # File watching
openai>=1.30           # OpenAI SDK
anthropic>=0.25        # Anthropic SDK
httpx>=0.27            # HTTP client
requests>=2.31         # HTTP requests
arxiv>=2.0             # arXiv API
beautifulsoup4>=4.12   # HTML parsing
lxml>=5.0              # XML/HTML parsing
jsonlines>=4.0         # JSONL processing
tenacity>=8.2          # Retry logic
tiktoken>=0.7          # Token counting
```

### Optional (lazy-loaded)
```
# TUI
textual>=0.70, textual-dev

# Desktop
tauri, vite, react, typescript

# Gateway
python-telegram-bot>=20, discord.py>=2.3, slack-sdk>=3, matrix-nio>=0.20, aiohttp

# Voice
faster-whisper>=1.0, groq>=0.4, elevenlabs>=0.3, mistral>=0.3, xai>=0.1, openai-tts>=0.1

# Image Generation
fal-client>=0.1

# MCP
mcp>=0.1, anyio>=4

# Browser
playwright>=1.40, browser-use, browserbase

# Dashboard/API
fastapi>=0.100, uvicorn>=0.23, websockets>=11

# Testing
pytest>=8.2, pytest-asyncio>=0.23, pytest-cov>=4.0, ruff>=0.4, mypy>=1.10, playwright>=1.40

# Local Embeddings
sentence-transformers>=3.0

# Docker
docker>=7.0

# CLI
nodeenv>=1.9
```

---

## 24. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Delegation complexity explosion | High | High | Strict budgets, max depth limits, circuit breakers |
| Subagent context pollution | Medium | High | Isolated contexts, explicit handoff protocols |
| Provider rate limits during parallel delegation | High | Medium | Built-in fallback, request queuing, local model option |
| Memory bloat from long delegations | Medium | Medium | Aggressive compression, lineage pruning |
| Skill/tool conflict with Hermes core | Low | High | Namespace isolation (`enaya_*` prefix), plugin boundaries |

---

## Additional Reference Documents

For more detailed information, see:

- **`README.md`** — Quick start, architecture overview, provider table
- **`AGENTS.md`** — Development guide (conventions, adding tools/providers)
- **`HERMES.md`** — Project context for Hermes architecture
- **`DEVELOPMENT_PLAN.md`** — Research & development plan with phases and risks
- **`IMPLEMENTATION_PLAN.md`** — Feature implementation plan with completion status
- **`skills/`** — Bundled skill documentation (5 SKILL.md files)
- **`tests/`** — Unit, integration, and E2E tests

---

## Quick Reference Card

```bash
# Install
pip install -e ".[dev]"

# Chat
enaya chat                    # Interactive
enaya chat -q "query"         # Single query

# Delegation
enaya delegate "task"         # Delegate to subagents

# Research
enaya research "query" --depth deep

# Planning
enaya plan "goal" --complexity moderate

# Model
enaya model openrouter:anthropic/claude-3.5-sonnet

# Interfaces
enaya tui                     # Textual TUI
enaya dashboard               # Web dashboard
enaya api-server              # FastAPI server
enaya acp                     # ACP server

# Config
enaya setup                   # Interactive setup
enaya config --list           # Show config

# Profile
enaya -p myprofile chat -q "test"

# Tests
pytest tests/ -n0 -q          # Full suite
pytest --cov=enaya --cov-fail-under=60  # Coverage
```

---

*Document generated: September 2026*  
*Based on Enaya Agent repository analysis*  
*Fork of Hermes Agent by Nous Research*
