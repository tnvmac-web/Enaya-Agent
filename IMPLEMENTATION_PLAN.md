# Enaya Agent — Feature Implementation Plan

## Current State (Completed)
- [x] Core Architecture (AIAgent, conversation_loop, prompt_builder, context_compressor)
- [x] Provider Resolution (15+ providers)
- [x] Session Storage (SQLite + FTS5 with lineage)
- [x] Tool System (50+ tools across 6 toolsets)
- [x] 5-Layer Memory (Session, Episodic, Semantic, Procedural, Project)
- [x] Delegation Engine (Orchestrator, TaskQueue, ResultAggregator, Policies)
- [x] Research Pipeline (WebResearcher, PaperAnalyzer, SourceValidator)
- [x] Planning Engine (TaskDecomposer, PlanBuilder, PlanValidator)
- [x] CLI Commands (chat, delegate, research, plan, model, setup, config)
- [x] Skills System (5 bundled skills)
- [x] Unit Tests (11 passing)

---

## Phase 1: Core Interfaces (Priority: High)

### 1.1 TUI (Ink Terminal UI)
**File**: `src/enaya/tui/`
- [ ] Ink-based terminal UI with mouse support
- [ ] Non-blocking input, rich overlays
- [ ] Session list, streaming tool output
- [ ] Widget apps (ticker, clock, dashboard)
- [ ] Command palette (Cmd+K)
- [ ] Configuration: `display.interface: tui`

### 1.2 Web Dashboard
**File**: `src/enaya/dashboard/`
- [ ] Admin panel with embedded chat
- [ ] Configuration management UI
- [ ] MCP server catalog
- [ ] Messaging platform pairing
- [ ] Webhook management
- [ ] Memory browser
- [ ] Profile builder
- [ ] OAuth/token authentication gate

### 1.3 API Server (OpenAI-Compatible)
**File**: `src/enaya/api_server/`
- [ ] `POST /v1/chat/completions` (streaming SSE)
- [ ] `POST /v1/responses` (stateful)
- [ ] `POST /v1/runs` / `GET /v1/runs/{id}` / `GET /v1/runs/{id}/events`
- [ ] `POST /v1/runs/{id}/approval` / `steer` / `stop`
- [ ] `GET /v1/capabilities`
- [ ] `GET /v1/models`
- [ ] `GET /api/model/options`
- [ ] Browser control endpoints

### 1.4 ACP Server (Agent Context Protocol)
**File**: `src/enaya/acp_adapter/`
- [ ] JSON-RPC over stdio
- [ ] Session creation, prompt submission
- [ ] Streaming chunks, tool-call events
- [ ] Permission requests, session fork, cancel
- [ ] Authentication

---

## Phase 2: Messaging Gateway (Priority: High)

### 2.1 Gateway Core
**File**: `src/enaya/gateway/`
- [ ] GatewayRunner message dispatch
- [ ] SessionStore (conversation persistence)
- [ ] Delivery (reply, cron, home channel, cross-platform)
- [ ] Authorization (allowlists, DM pairing)
- [ ] Slash command dispatch
- [ ] Hook system (gateway:startup, session:*, agent:*, command:*)
- [ ] Cron ticking
- [ ] Token locks, profile-scoped process tracking

### 2.2 Platform Adapters (Start with core 5)
- [ ] Telegram
- [ ] Discord
- [ ] Slack
- [ ] Matrix
- [ ] Email (IMAP/SMTP)

### 2.3 Additional Platforms (Phase 2b)
- [ ] WhatsApp (Baileys)
- [ ] Signal
- [ ] SMS (Twilio)
- [ ] Microsoft Teams
- [ ] Google Chat
- [ ] Webhooks

---

## Phase 3: Media & AI Features (Priority: Medium)

### 3.1 Voice Mode
**File**: `src/enaya/voice/`
- [ ] Real-time voice conversations
- [ ] STT providers (local faster-whisper, Groq, OpenAI, ElevenLabs)
- [ ] TTS providers (local, OpenAI, ElevenLabs, Mistral, xAI)
- [ ] Wake word ("Hey Enaya")
- [ ] Telegram/Discord voice channel support

### 3.2 Browser Automation
**File**: `src/enaya/browser/`
- [ ] CDP local Chromium
- [ ] Browserbase cloud
- [ ] Agent-browser facade
- [ ] Form filling, scraping
- [ ] Stealth modes

### 3.3 Vision
**File**: `src/enaya/vision/`
- [ ] Clipboard image paste
- [ ] Multimodal analysis
- [ ] Image attachment in chat

### 3.4 Image Generation
**File**: `src/enaya/image_gen/`
- [ ] FAL.ai integration (FLUX 2, GPT Image, etc.)
- [ ] Model selection via `enaya tools`
- [ ] Free tier support

### 3.5 TTS/STT
**File**: `src/enaya/tts/` and `src/enaya/stt/`
- [ ] Multiple provider backends
- [ ] Voice message transcription
- [ ] Text-to-speech across platforms

---

## Phase 4: Extensibility & UX (Priority: Medium)

### 4.1 Plugin System
**File**: `src/enaya/plugins/`
- [ ] PluginManager (discovery, loading, hooks)
- [ ] Three sources: bundled, user (`~/.enaya/plugins/`), project (`.enaya/plugins/`)
- [ ] Tool, hook, CLI command, skill registration
- [ ] Memory providers, context engines
- [ ] Platform adapters as plugins

### 4.2 Themes/Skins
**File**: `src/enaya/themes/`
- [ ] Built-in skins (dark, light, synthwave, etc.)
- [ ] Custom skin YAML
- [ ] Live reload across all surfaces
- [ ] `enaya skin set <key> <hex>`
- [ ] Per-surface palette

### 4.3 Pets (Mascots)
**File**: `src/enaya/pets/`
- [ ] Animated mascots
- [ ] React to agent activity
- [ ] CLI, TUI, desktop integration

### 4.4 MCP Support
**File**: `src/enaya/mcp/`
- [ ] MCP client facade
- [ ] Tool filtering
- [ ] Server lifecycle management

---

## Phase 5: Automation & Orchestration (Priority: Medium)

### 5.1 Cron Jobs (Full Implementation)
**File**: `src/enaya/cron/`
- [ ] JSON storage (`~/.enaya/cron/jobs.json`)
- [ ] Multiple schedules (cron, interval, one-shot)
- [ ] Skill attachment
- [ ] Cross-platform delivery
- [ ] Fallback model support

### 5.2 Kanban
**File**: `src/enaya/kanban/`
- [ ] SQLite-backed task board
- [ ] Multi-agent coordination
- [ ] Worker lanes
- [ ] Single dispatcher

### 5.3 Hooks
**File**: `src/enaya/hooks/`
- [ ] Lifecycle hooks (session:*, agent:*, command:*)
- [ ] Webhook triggers
- [ ] Custom code execution

### 5.4 Batch Processing
**File**: `src/enaya/batch/`
- [ ] Parallel trajectory generation
- [ ] Checkpointing
- [ ] Toolset distributions

---

## Phase 6: Platform & Distribution (Priority: High for Windows)

### 6.1 Windows Installer
**File**: `installers/windows/`
- [ ] NSIS installer
- [ ] UV + Python + venv setup
- [ ] Launcher creation
- [ ] PATH configuration
- [ ] Uninstaller

### 6.2 CI/CD Pipeline
**File**: `.github/workflows/`
- [ ] Test workflow (pytest, ruff, mypy, coverage)
- [ ] Build workflow (Windows NSIS, macOS DMG, Linux AppImage)
- [ ] Release workflow (auto-tag, artifacts, changelog)
- [ ] Desktop app build (Electron/Tauri)
- [ ] Rust toolchain check for desktop

### 6.3 Desktop App (Electron/Tauri)
**File**: `desktop/`
- [ ] Tauri + React/Vite frontend
- [ ] Streaming chat
- [ ] Session list
- [ ] File browser
- [ ] Voice integration
- [ ] Native notifications
- [ ] Profile remote-gateway login
- [ ] Desktop UI plugins

---

## Phase 7: Advanced Features (Priority: Low)

### 7.1 Profiles Enhancement
- [ ] Full isolation (config, sessions, skills, memory, gateway PID)
- [ ] Profile distributions (share whole agent)
- [ ] Multi-gateway concurrent run

### 7.2 Context Files
- [ ] `.enaya.md` / `ENAYA.md` (walks to git root)
- [ ] `AGENTS.md`, `CLAUDE.md` (CWD only)
- [ ] `.cursorrules` support

### 7.3 Personality/SOUL.md
- [ ] Global SOUL.md
- [ ] Built-in personalities
- [ ] Custom persona definitions

### 7.4 Security Features
- [ ] Dangerous command approval
- [ ] Secret redaction
- [ ] PII protection
- [ ] Checkpoints & rollback (shadow git)

### 7.5 Import from Other Agents
- [ ] Claude Code (~/.claude) import
- [ ] OpenAI Codex (~/.codex) import

---

## Implementation Order (Recommended)

```
Week 1-2:  Phase 1.1-1.4  (Core Interfaces: TUI, Dashboard, API, ACP)
Week 3-4:  Phase 2.1-2.2  (Gateway Core + 5 Platform Adapters)
Week 5-6:  Phase 3.1-3.5  (Voice, Browser, Vision, Image, TTS)
Week 7-8:  Phase 4.1-4.4  (Plugins, Themes, Pets, MCP)
Week 9-10: Phase 5.1-5.4  (Cron, Kanban, Hooks, Batch)
Week 11-12: Phase 6.1-6.3  (Installer, CI/CD, Desktop App)
Week 13-14: Phase 7        (Advanced Features)
```

---

## Dependencies to Add

```toml
# TUI
[project.optional-dependencies]
tui = ["textual>=0.70", "textual-dev"]

# Desktop
desktop = ["tauri", "vite", "react", "typescript"]

# Gateway
gateway = ["python-telegram-bot>=20", "discord.py>=2.3", "slack-sdk>=3", "matrix-nio>=0.20", "aiohttp"]

# Voice
voice = ["faster-whisper", "groq", "elevenlabs", "mistral", "xai", "openai-tts"]

# Browser
browser = ["playwright", "browser-use", "browserbase"]

# Image
image_gen = ["fal-client"]

# MCP
mcp = ["mcp", "anyio"]

# Installer
installer = ["nsis", "makensis"]
```

---

## Quick Wins (Can Do Immediately)

1. [ ] Add `enaya --tui` command stub
2. [ ] Add `enaya dashboard` command stub
3. [ ] Add `enaya api-server` command stub
4. [ ] Add `enaya acp` command stub
5. [ ] Implement cron job storage + basic scheduler
6. [ ] Add webhook endpoint to API server
7. [ ] Create basic desktop app skeleton (Tauri)
8. [ ] Add CI workflow for tests + lint

---

## Success Criteria per Phase

| Phase | Criteria |
|-------|----------|
| 1 | All 4 interfaces launch and respond to basic queries |
| 2 | Gateway runs, 5 platforms connect, send/receive messages |
| 3 | Voice chat works, browser navigates, image generates |
| 4 | Plugin loads, theme applies, pet animates, MCP connects |
| 5 | Cron fires, Kanban board works, hooks trigger |
| 6 | Installer builds, CI passes, desktop app launches |
| 7 | Profiles isolated, import works, security features active |