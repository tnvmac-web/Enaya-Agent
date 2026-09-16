# Enaya Agent

**Task-delegation AI agent with multi-agent orchestration, deep research, and structured planning.**

Built on Hermes Agent architecture principles — local-first, multi-provider, extensible.

## Quick Install

```bash
# From source
git clone https://github.com/tnvmac-web/Enaya-Agent.git
cd Enaya-Agent
pip install -e ".[dev]"

# Or install directly (when published)
pip install enaya-agent
```

## Quick Start

```bash
# Interactive chat
enaya chat

# Single query
enaya chat -q "Research the latest LLM agent architectures"

# Delegate a complex task
enaya delegate "Build a REST API with authentication and tests"

# Deep research
enaya research "Current state of distributed caching" --depth deep

# Create a plan
enaya plan "Implement user authentication system" --complexity moderate

# Switch model
enaya model openrouter:anthropic/claude-3.5-sonnet

# Setup wizard
enaya setup
```

## Core Capabilities

| Capability | Description |
|------------|-------------|
| **Delegation** | Spawn specialized subagents for parallel task execution |
| **Research** | Web search, academic papers, source validation, synthesis |
| **Planning** | Hierarchical task decomposition, phased execution plans |
| **Memory** | 5-layer persistent memory (Session, Episodic, Semantic, Procedural, Project) |
| **Codebase** | Code search, analysis, modification, testing |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Enaya Agent                             │
├─────────────────────────────────────────────────────────────┤
│  AIAgent (run_agent.py) — Single class, all entry points   │
├─────────────────────────────────────────────────────────────┤
│  Agent Loop          │  Prompt System      │  Provider Res  │
│  conversation_loop   │  prompt_builder     │  runtime_      │
│  context_compressor  │  anthropic_adapter  │  provider      │
├─────────────────────────────────────────────────────────────┤
│  Tools (50+)         │  Delegation         │  Memory        │
│  registry            │  orchestrator       │  5-layer       │
│  file/web/delegation │  task_queue         │  SQLite+Chroma │
│  research/planning   │  result_aggregator  │  project_index │
│  synthesis           │  policies           │                │
├─────────────────────────────────────────────────────────────┤
│  Interfaces: CLI • ACP (VS Code/Zed) • API Server • Gateway │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

```yaml
# ~/.enaya/config.yaml
model: "openrouter:anthropic/claude-3.5-sonnet"
provider: "openrouter"
max_turns: 500
temperature: 0.7
toolsets: ["core", "research", "planning", "delegation", "synthesis"]
fallback_providers: []
compression_threshold: 0.50
prompt_caching: true
```

```bash
# ~/.enaya/.env
OPENROUTER_API_KEY=sk-...
ANTHROPIC_TOKEN=sk-ant-...
OPENAI_API_KEY=sk-...
NVIDIA_API_KEY=...
```

## Providers Supported

| Provider | Models | API Mode |
|----------|--------|----------|
| OpenRouter | Claude, GPT, Gemini, Llama, Nemotron | chat_completions |
| Anthropic | Claude 3.5 Sonnet/Haiku/Opus | anthropic_messages |
| OpenAI | GPT-4o, GPT-4o-mini, o1 | chat_completions |
| NVIDIA | Nemotron 3 Ultra, Llama 3.1 | chat_completions |
| Google | Gemini 1.5 Pro/Flash | chat_completions |
| Ollama | Local models | chat_completions |
| LM Studio | Local models | chat_completions |

## Skills (Bundled)

| Skill | Purpose |
|-------|---------|
| `enaya-research` | Deep research workflow |
| `enaya-planning` | Task decomposition & plan creation |
| `enaya-delegation` | Multi-agent orchestration |
| `enaya-code-review` | Automated code review |
| `enaya-doc-audit` | Documentation drift detection |

## Programmatic Integration

### ACP (VS Code, Zed, JetBrains)
```bash
enaya acp  # Starts JSON-RPC stdio server
```

### API Server (OpenAI-compatible)
```bash
enaya api-server  # Starts HTTP + SSE server
```

### Python Embedding
```python
from enaya.run_agent import create_agent

agent = create_agent(model="openrouter:anthropic/claude-3.5-sonnet")
result = agent.run_conversation("Research quantum computing advances")
```

## Development

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Test
pytest tests/ -n0 -q

# Lint
ruff check src/

# Type check
mypy src/enaya/

# Coverage
pytest --cov=enaya --cov-fail-under=60
```

## Project Structure

```
enaya-agent/
├── src/enaya/              # Core package
│   ├── agent/              # Agent loop & prompts
│   ├── cli/                # CLI commands
│   ├── tools/              # 50+ built-in tools
│   ├── delegation/         # Multi-agent orchestration
│   ├── research/           # Research pipeline
│   ├── planning/           # Planning engine
│   ├── memory/             # 5-layer memory
│   ├── gateway/            # Messaging gateway
│   ├── acp_adapter/        # ACP server
│   └── plugins/            # Plugin system
├── skills/                 # Bundled skills
├── tests/                  # Unit/integration/e2e
├── docs/                   # Documentation
├── pyproject.toml
├── AGENTS.md               # Development guide
├── HERMES.md               # Project context
└── README.md
```

## Design Principles

- **Platform-Agnostic Core**: One `AIAgent` serves CLI, gateway, ACP, API server
- **Observable Execution**: Every tool call visible via callbacks
- **Interruptible**: API calls and tools cancellable mid-flight
- **Loose Coupling**: Optional subsystems use registry patterns
- **Profile Isolation**: Multiple concurrent instances via `enaya -p <name>`

## License

MIT License — see LICENSE file.

## References

- Hermes Agent Architecture: https://hermes-agent.nousresearch.com/docs/developer-guide/architecture
- Original Hermes: https://github.com/NousResearch/hermes-agent