"""
Enaya Agent - Prompt Builder
System prompt assembly (stable → context → volatile).
Mirrors Hermes Agent's agent/prompt_builder.py exactly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from enaya.run_agent import AIAgent


# =============================================================================
# Default Agent Identity (replaced by SOUL.md when present)
# =============================================================================

DEFAULT_AGENT_IDENTITY = """You are Enaya Agent — a task-delegation AI agent specialized in research, planning, and multi-agent orchestration.

## Core Capabilities
- **Delegation**: Break complex tasks into subtasks and spawn specialized subagents
- **Research**: Deep web search, academic paper analysis, source validation, synthesis
- **Planning**: Hierarchical task decomposition, structured plan creation, validation
- **Synthesis**: Multi-source result aggregation, comparison, claim extraction
- **Codebase**: Search, analyze, modify, and test code across repositories

## Working Style
- Think before acting: decompose → plan → delegate → synthesize
- Prefer parallel subagent execution for independent subtasks
- Always cite sources and provide provenance for claims
- Maintain context across long-running delegations via compression
- Surface uncertainties and conflicting evidence explicitly

## Tool Usage
- Use `delegate_task` for complex subtasks requiring independent context
- Use `web_search` + `web_extract` for current information
- Use `arxiv_search` + `paper_analyze` for academic sources
- Use `task_decompose` + `plan_create` for structured planning
- Use `synthesize_results` to merge subagent outputs
- Use `code_search` / `code_analyze` for codebase tasks
- Batch independent tool calls when possible

## Output Format
- Be concise but thorough
- Use structured formatting (tables, lists, headers) for complex answers
- Always include a summary for multi-step operations
- Flag when compression has occurred in long conversations"""


# =============================================================================
# System Prompt Builder
# =============================================================================

def build_system_prompt(
    agent: AIAgent,
    tool_schemas: list[dict],
    *,
    skip_soul: bool = False,
) -> str:
    """
    Build the three-tier system prompt: stable → context → volatile.
    Cached across turns unless explicitly rebuilt.
    """
    parts = []

    # ===== STABLE TIER =====
    # 1. Agent Identity (SOUL.md or default)
    if not skip_soul:
        soul_content = load_soul_md(agent.config.profile)
        if soul_content:
            parts.append(soul_content)
        else:
            parts.append(DEFAULT_AGENT_IDENTITY)

    # 2. Tool Guidance (auto-generated from schemas)
    if tool_schemas:
        parts.append(build_tool_guidance(tool_schemas))

    # 3. Active Skills (descriptions + tool references)
    skills_prompt = build_skills_prompt(agent)
    if skills_prompt:
        parts.append(skills_prompt)

    stable_prompt = "\n\n---\n\n".join(parts)

    # ===== CONTEXT TIER =====
    # Project context files (loaded once per session)
    context_prompt = build_context_files_prompt(agent, skip_soul=skip_soul)
    if context_prompt:
        stable_prompt += "\n\n---\n\n" + context_prompt

    # ===== VOLATILE TIER =====
    # Added at API call time, not cached:
    # - Memory snapshots (MEMORY.md + USER.md)
    # - Profile data
    # - Timestamp
    # - Platform hints
    # These are injected via build_volatile_prompt() at call time

    return stable_prompt


def build_volatile_prompt(agent: AIAgent) -> str:
    """Build the volatile tier (rebuilt each turn)."""
    parts = []

    # Memory snapshots
    memory_content = load_memory_snapshot(agent.config.profile)
    if memory_content:
        parts.append("## Memory\n" + memory_content)

    # Profile data
    profile_data = get_profile_data(agent.config.profile)
    if profile_data:
        parts.append("## Profile\n" + profile_data)

    # Timestamp
    from datetime import datetime
    parts.append(f"## Current Time\n{datetime.now().isoformat()}")

    # Platform hint
    parts.append(f"## Platform\n{agent.config.platform}")

    return "\n\n---\n\n".join(parts)


# =============================================================================
# Tool Guidance
# =============================================================================

def build_tool_guidance(tool_schemas: list[dict]) -> str:
    """Generate tool usage guidance from schemas."""
    if not tool_schemas:
        return ""

    lines = ["## Available Tools", ""]
    for schema in tool_schemas:
        fn = schema.get("function", {})
        name = fn.get("name", "unknown")
        desc = fn.get("description", "No description")
        params = fn.get("parameters", {})
        required = params.get("required", [])
        props = params.get("properties", {})

        lines.append(f"### `{name}`")
        lines.append(desc)
        if props:
            lines.append("**Parameters:**")
            for prop_name, prop_info in props.items():
                req = " (required)" if prop_name in required else ""
                prop_desc = prop_info.get("description", "")
                lines.append(f"  - `{prop_name}`{req}: {prop_desc}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# Skills Prompt
# =============================================================================

def build_skills_prompt(agent: AIAgent) -> str:
    """Build active skills descriptions."""
    # Skills are loaded from skills/ directory and config
    # For now, return empty - skills system to be implemented
    return ""


# =============================================================================
# Context Files (Project Context)
# =============================================================================

def build_context_files_prompt(agent: AIAgent, *, skip_soul: bool = False) -> str:
    """
    Load project context files in priority order:
    1. .hermes.md / HERMES.md (walks to git root)
    2. AGENTS.md (CWD only)
    3. CLAUDE.md (CWD only)
    4. .cursorrules / .cursor/rules/*.mdc (CWD only)
    Only FIRST match wins.
    """
    cwd = Path.cwd()
    context_files = [
        (find_context_file(cwd, [".hermes.md", "HERMES.md"]), "HERMES.md"),
        (cwd / "AGENTS.md", "AGENTS.md"),
        (cwd / "CLAUDE.md", "CLAUDE.md"),
        (cwd / ".cursorrules", ".cursorrules"),
    ]

    # Also check .cursor/rules/*.mdc
    cursor_rules_dir = cwd / ".cursor" / "rules"
    if cursor_rules_dir.exists():
        for mdc in sorted(cursor_rules_dir.glob("*.mdc")):
            context_files.append((mdc, f".cursor/rules/{mdc.name}"))

    for path, label in context_files:
        if path and path.exists():
            content = read_context_file(path)
            if content:
                return f"## Project Context ({label})\n\n{content}"

    return ""


def find_context_file(start: Path, names: list[str]) -> Path | None:
    """Walk up directory tree to find context file (for .hermes.md/HERMES.md)."""
    current = start
    while current != current.parent:
        for name in names:
            candidate = current / name
            if candidate.exists():
                return candidate
        current = current.parent
    return None


def read_context_file(path: Path) -> str:
    """Read and sanitize context file."""
    try:
        content = path.read_text(encoding="utf-8")
        # Strip YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2]
        # Truncate based on model context (handled by caller)
        return content.strip()
    except Exception:
        return ""


# =============================================================================
# SOUL.md Loading
# =============================================================================

def load_soul_md(profile: str) -> str | None:
    """Load SOUL.md for the given profile."""
    # Check profile-specific location
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    # For Enaya, use ENAYA_HOME or same location
    enaya_home = Path(os.environ.get("ENAYA_HOME", hermes_home))
    profile_dir = enaya_home / "profiles" / profile if (enaya_home / "profiles").exists() else enaya_home

    for path in [profile_dir / "SOUL.md", enaya_home / "SOUL.md"]:
        if path.exists():
            try:
                return path.read_text(encoding="utf-8").strip()
            except Exception:
                pass
    return None


# =============================================================================
# Memory Snapshots
# =============================================================================

def load_memory_snapshot(profile: str) -> str:
    """Load MEMORY.md and USER.md for volatile tier."""
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    enaya_home = Path(os.environ.get("ENAYA_HOME", hermes_home))
    profile_dir = enaya_home / "profiles" / profile if (enaya_home / "profiles").exists() else enaya_home

    parts = []
    for name in ["MEMORY.md", "USER.md"]:
        for path in [profile_dir / name, enaya_home / name]:
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8").strip()
                    if content:
                        parts.append(f"### {name}\n{content}")
                except Exception:
                    pass
                break

    return "\n\n".join(parts)


# =============================================================================
# Profile Data
# =============================================================================

def get_profile_data(profile: str) -> str:
    """Get profile-specific configuration data."""
    # Could include model preferences, toolset config, etc.
    return f"Active profile: {profile}"


# =============================================================================
# Prompt Caching (Anthropic)
# =============================================================================

def apply_prompt_caching(messages: list[dict], *, cache_ttl: str = "5m") -> list[dict]:
    """
    Apply Anthropic prompt caching markers (cache_control) to messages.
    Strategy: system_and_3 (4 breakpoints max).
    """
    # Find non-system messages
    non_system_indices = [i for i, m in enumerate(messages) if m["role"] != "system"]

    # BP1: System prompt (always cached)
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = [
            {"type": "text", "text": messages[0]["content"], "cache_control": {"type": "ephemeral", "ttl": cache_ttl}}
        ]

    # BP2-4: 3rd-to-last, 2nd-to-last, last non-system messages
    if len(non_system_indices) >= 3:
        for offset, idx in enumerate([-3, -2, -1]):
            msg_idx = non_system_indices[idx]
            if isinstance(messages[msg_idx]["content"], str):
                messages[msg_idx]["content"] = [
                    {"type": "text", "text": messages[msg_idx]["content"], "cache_control": {"type": "ephemeral", "ttl": cache_ttl}}
                ]

    return messages


def estimate_cache_savings(messages: list[dict]) -> dict:
    """Estimate token savings from prompt caching."""
    cached_tokens = 0
    total_tokens = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            for block in content:
                if block.get("cache_control"):
                    cached_tokens += len(block.get("text", "")) // 4  # rough estimate
                total_tokens += len(block.get("text", "")) // 4
        else:
            total_tokens += len(content) // 4

    return {
        "cached_tokens": cached_tokens,
        "total_tokens": total_tokens,
        "savings_pct": (cached_tokens / total_tokens * 100) if total_tokens > 0 else 0,
    }
