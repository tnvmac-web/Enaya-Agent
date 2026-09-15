# Enaya Agent — Research & Development Plan

## Project Overview
**Enaya Agent** — A task-delegation focused AI agent built on Hermes Agent architecture principles, designed for autonomous multi-agent workflows with emphasis on research, planning, and delegation capabilities.

**Core Philosophy**: "Delegate, Research, Execute" — An agent that specializes in breaking down complex tasks, delegating to specialized subagents, and synthesizing results.

---

## Phase 1: Discovery & Architecture (Week 1-2)

### 1.1 Architecture Decisions
Based on Hermes Agent architecture, Enaya will adopt:

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **Core Loop** | Fork `AIAgent` / `run_conversation()` | Proven, battle-tested agent loop |
| **Memory** | 5-layer (Session, Episodic, Semantic, Procedural, Project) | Matches X-Copilot memory subsystem |
| **Delegation** | Native `delegate_task` tool + subagent orchestration | Built into Hermes, proven at scale |
| **Provider** | Multi-provider (OpenRouter, Anthropic, NVIDIA, Local) | Hermes supports 28+ providers |
| **Tools** | Core + Research-focused toolsets | Extend Hermes tool registry |
| **Interface** | CLI + TUI + ACP (VS Code) + API Server | Hermes supports all three |
| **Session Storage** | SQLite + FTS5 (Hermes `hermes_state.py`) | Proven, lineage tracking |
| **Context Compression** | Hermes `ContextCompressor` (50% threshold) | Handles long-running delegations |

### 1.2 Enaya-Specific Extensions

#### New Toolsets
| Toolset | Tools | Purpose |
|---------|-------|---------|
| `research` | `web_search`, `web_extract`, `arxiv_search`, `paper_analyze` | Deep research capabilities |
| `planning` | `task_decompose`, `plan_create`, `plan_update`, `plan_review` | Structured planning |
| `delegation` | `delegate_task`, `subagent_status`, `subagent_steer`, `subagent_stop` | Multi-agent orchestration |
| `synthesis` | `synthesize_results`, `compare_sources`, `extract_claims` | Result aggregation |
| `codebase` | `code_search`, `code_analyze`, `code_modify`, `test_run` | Codebase interaction |

#### New Skills (Bundled)
| Skill | Description |
|-------|-------------|
| `enaya-research` | Deep research workflow: query → search → extract → synthesize |
| `enaya-planning` | Task decomposition → plan → validate → execute |
| `enaya-delegation` | Subagent spawning, monitoring, result collection |
| `enaya-code-review` | Automated code review with security/quality gates |
| `enaya-doc-audit` | Documentation vs codebase drift detection |

### 1.3 Directory Structure
```
enaya-agent/
├── enaya/                          # Core package
│   ├── __init__.py
│   ├── agent.py                    # EnayaAgent (extends AIAgent)
│   ├── conversation_loop.py        # Extended agent loop with delegation awareness
│   ├── prompt_builder.py           # Enaya-specific prompt assembly
│   ├── delegation/
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Subagent lifecycle management
│   │   ├── task_queue.py           # Task distribution & priorities
│   │   ├── result_aggregator.py    # Collect & synthesize subagent results
│   │   └── policies.py             # Delegation policies (when/how to delegate)
│   ├── research/
│   │   ├── __init__.py
│   │   ├── web_researcher.py       # Web search + extraction pipeline
│   │   ├── paper_analyzer.py       # Academic paper processing
│   │   └── source_validator.py     # Credibility scoring
│   ├── planning/
│   │   ├── __init__.py
│   │   ├── task_decomposer.py      # Break tasks into subtasks
│   │   ├── plan_builder.py         # Structured plan creation
│   │   └── plan_validator.py       # Plan quality checks
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── five_layer.py           # 5-layer memory implementation
│   │   ├── semantic_store.py       # ChromaDB integration
│   │   └── project_indexer.py      # Codebase knowledge graph
│   └── tools/
│       ├── __init__.py
│       ├── research_tools.py
│       ├── planning_tools.py
│       ├── delegation_tools.py
│       └── synthesis_tools.py
├── cli/
│   ├── main.py                     # CLI entry point
│   ├── commands.py                 # Slash commands
│   └── config.py                   # Configuration
├── gateway/                        # Optional: messaging gateway
├── acp_adapter/                    # ACP server for IDE integration
├── plugins/
│   ├── model-providers/
│   ├── platforms/
│   └── memory/
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

---

## Phase 2: Implementation (Week 3-6)

### 2.1 Sprint 1: Core Foundation (Week 3)
- [ ] Project scaffolding (pyproject.toml, directory structure)
- [ ] `EnayaAgent` class extending `AIAgent`
- [ ] Custom `conversation_loop.py` with delegation checkpoints
- [ ] Prompt builder with Enaya identity (SOUL.md)
- [ ] Configuration system (config.yaml, .env)
- [ ] Basic CLI with `enaya chat`, `enaya delegate`, `enaya research`

### 2.2 Sprint 2: Delegation Engine (Week 4)
- [ ] `DelegationOrchestrator` — subagent spawn/monitor/collect
- [ ] `TaskQueue` — priority-based task distribution
- [ ] `ResultAggregator` — collect, deduplicate, synthesize
- [ ] Delegation policies (complexity thresholds, domain routing)
- [ ] Subagent budget management (iterations, tokens, cost)
- [ ] Integration with Hermes `delegate_task` tool

### 2.3 Sprint 3: Research Pipeline (Week 5)
- [ ] `WebResearcher` — search → extract → validate → summarize
- [ ] `PaperAnalyzer` — arXiv/PDF ingestion → structured extraction
- [ ] `SourceValidator` — credibility scoring, bias detection
- [ ] Research skill (`enaya-research`) with workflow
- [ ] Integration with Supermemory for cross-session recall

### 2.4 Sprint 4: Planning & Synthesis (Week 6)
- [ ] `TaskDecomposer` — hierarchical task breakdown
- [ ] `PlanBuilder` — structured plans with milestones
- [ ] `PlanValidator` — feasibility, completeness checks
- [ ] `SynthesisEngine` — multi-source result merging
- [ ] Planning skill (`enaya-planning`)
- [ ] Synthesis tools

---

## Phase 3: Testing (Week 7)

### 3.1 Test Strategy
| Level | Coverage | Tools |
|-------|----------|-------|
| Unit | ≥90% | pytest, pytest-asyncio |
| Integration | ≥80% | Full agent loops, delegation flows |
| E2E | Key paths | Real delegation scenarios |
| Provider Parity | All providers | `test_provider_parity.py` pattern |

### 3.2 Key Test Scenarios
- [ ] Single-task delegation → result synthesis
- [ ] Multi-subagent parallel delegation
- [ ] Subagent failure handling & retry
- [ ] Research pipeline: query → 10 sources → synthesis
- [ ] Planning: complex task → validated plan → execution
- [ ] Memory persistence across sessions
- [ ] Context compression during long delegations
- [ ] Provider fallback during delegation

---

## Phase 4: Documentation (Week 8)

### 4.1 Required Documentation
- [ ] `README.md` — Quick start, architecture overview
- [ ] `AGENTS.md` — Development guide (this project's conventions)
- [ ] `HERMES.md` — Project context for Hermes
- [ ] `docs/architecture.md` — System design
- [ ] `docs/delegation.md` — Delegation patterns
- [ ] `docs/research.md` — Research workflows
- [ ] `docs/skills.md` — Bundled skills reference
- [ ] `docs/api.md` — Programmatic integration (ACP, TUI Gateway, API Server)
- [ ] `CONTRIBUTING.md`

### 4.2 Skill Documentation
Each bundled skill needs:
- `SKILL.md` with frontmatter
- Usage examples
- Tool references

---

## Phase 5: Validation & Release (Week 9-10)

### 5.1 Validation Checklist
- [ ] `pytest tests/ -n0 -q` — full suite passes
- [ ] `ruff check .` — linting clean
- [ ] `mypy enaya/` — type checking clean
- [ ] Coverage ≥60% (match Hermes gate)
- [ ] `enaya chat -q "test"` — smoke test
- [ ] `enaya delegate "research X and build Y"` — delegation test
- [ ] ACP server starts: `enaya acp`
- [ ] API server starts: `enaya api-server`
- [ ] Gateway starts: `enaya gateway start`

### 5.2 Release Artifacts
- [ ] PyPI package: `pip install enaya-agent`
- [ ] GitHub Release with changelog
- [ ] Documentation site (Docusaurus like Hermes)
- [ ] Installer script (PowerShell like Hermes)

---

## Dependencies

### Core (from Hermes)
```
# Runtime
pydantic>=2.7
pyyaml>=6.0
rich>=13.7
click>=8.1
chromadb>=0.5
networkx>=3.2
watchdog>=3.0

# LLM Providers
openai>=1.30
anthropic>=0.25
httpx>=0.27

# Research
arxiv>=2.0
requests>=2.31
beautifulsoup4>=4.12
lxml>=5.0

# Testing
pytest>=8.2
pytest-asyncio>=0.23
pytest-cov>=4.0
ruff>=0.4
mypy>=1.10
```

### Optional (lazy-loaded)
```
# Browser automation
playwright>=1.40

# Code execution
python-docker>=0.7  # for sandbox env

# Vector search (alternatives)
sentence-transformers>=3.0  # local embeddings
```

---

## Risk Assessment & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Delegation complexity explosion | High | High | Strict budgets, max depth limits, circuit breakers |
| Subagent context pollution | Medium | High | Isolated contexts, explicit handoff protocols |
| Provider rate limits during parallel delegation | High | Medium | Built-in fallback, request queuing, local model option |
| Memory bloat from long delegations | Medium | Medium | Aggressive compression, lineage pruning |
| Skill/tool conflict with Hermes core | Low | High | Namespace isolation (`enaya_*` prefix), plugin boundaries |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Delegation success rate | ≥95% |
| Research synthesis quality (human eval) | ≥4.5/5 |
| Plan execution completion | ≥90% |
| Context compression ratio | ≤30% token retention |
| Subagent spawn latency | <2s |
| Test coverage | ≥60% |
| Cold start time | <3s |

---

## Next Steps

1. **Immediate**: Create project scaffolding and `EnayaAgent` base class
2. **Week 1**: Implement delegation orchestrator and task queue
3. **Week 2**: Build research pipeline and planning tools
4. **Week 3**: Integrate skills, write tests, document
5. **Week 4**: Validation, polish, release prep

---

## Appendix: Hermes Architecture Leverage Points

Enaya directly reuses these Hermes components (no rewrite needed):
- `run_agent.py` → `AIAgent` facade
- `agent/conversation_loop.py` → core loop (extend, don't replace)
- `agent/prompt_builder.py` → prompt assembly (customize tiers)
- `agent/context_compressor.py` → compression (use as-is)
- `tools/registry.py` → tool registry (extend with enaya tools)
- `model_tools.py` → tool dispatch (use as-is)
- `hermes_state.py` → session storage (use as-is)
- `hermes_cli/runtime_provider.py` → provider resolution (use as-is)
- `acp_adapter/` → ACP server (use as-is)
- `gateway/` → messaging gateway (optional, use as-is)
- `plugins/` → plugin system (extend with enaya plugins)

Only Enaya-specific logic needs new code: delegation orchestration, research pipeline, planning engine, synthesis.