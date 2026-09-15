"""
Enaya Agent - Context Compressor
Default context engine (lossy summarization).
Mirrors Hermes Agent's agent/context_compressor.py exactly.
"""

from __future__ import annotations

import json
import tiktoken
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from enaya.run_agent import AIAgent

from enaya.agent.prompt_builder import build_system_prompt, build_volatile_prompt
from enaya.model_tools import collect_tool_schemas


@dataclass
class CompressionConfig:
    threshold: float = 0.50
    protect_last_n: int = 20
    summary_ratio: float = 0.20
    min_summary_tokens: int = 2000
    max_summary_tokens: int = 12000
    in_place: bool = True


class ContextCompressor:
    """
    Default context engine — lossy summarization algorithm.
    Runs before API call (preflight) when context exceeds threshold.
    Creates child session (new lineage ID).
    """

    def __init__(
        self,
        threshold: float = 0.50,
        protect_last_n: int = 20,
        summary_ratio: float = 0.20,
        min_summary_tokens: int = 2000,
        max_summary_tokens: int = 12000,
        in_place: bool = True,
    ):
        self.config = CompressionConfig(
            threshold=threshold,
            protect_last_n=protect_last_n,
            summary_ratio=summary_ratio,
            min_summary_tokens=min_summary_tokens,
            max_summary_tokens=max_summary_tokens,
            in_place=in_place,
        )
        self._tokenizer = None

    def _get_tokenizer(self):
        """Get tokenizer for token counting."""
        if self._tokenizer is None:
            try:
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # Fallback: rough character-based estimation
                self._tokenizer = None
        return self._tokenizer

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        tok = self._get_tokenizer()
        if tok:
            return len(tok.encode(text))
        return len(text) // 4  # rough estimate

    def count_message_tokens(self, message: dict) -> int:
        """Count tokens in a message dict."""
        content = message.get("content", "")
        if isinstance(content, list):
            return sum(self.count_tokens(block.get("text", "")) for block in content)
        return self.count_tokens(str(content))

    def get_context_window(self, model: str) -> int:
        """Get context window for model."""
        # Per-model overrides (from model_metadata)
        model_windows = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "claude-3-opus": 200000,
            "claude-3-sonnet": 200000,
            "claude-3-haiku": 200000,
            "claude-3.5-sonnet": 200000,
            "claude-3.7-sonnet": 200000,
            "gemini-1.5-pro": 2000000,
            "gemini-1.5-flash": 1000000,
        }
        for key, window in model_windows.items():
            if key in model.lower():
                return window
        return 128000  # default

    def should_compress(self, conversation_history: list[dict], model: str) -> bool:
        """Check if conversation exceeds compression threshold."""
        context_window = self.get_context_window(model)
        total_tokens = sum(self.count_message_tokens(msg) for msg in conversation_history)
        # Also include system prompt estimate
        total_tokens += 4000  # rough system prompt estimate
        return (total_tokens / context_window) >= self.config.threshold

    def compress(self, agent: AIAgent) -> None:
        """
        Compress conversation history via structured summarization.
        Creates child session with new lineage ID.
        """
        # Phase 1: Flush memory first (prevents data loss)
        agent._flush_memory()

        history = agent.conversation_history
        protect_n = self.config.protect_last_n

        # Phase 2: Determine boundaries
        head = history[:protect_n]
        tail = history[-protect_n:] if len(history) > protect_n else []
        middle = history[protect_n:-protect_n] if len(history) > protect_n * 2 else []

        if not middle:
            return  # Nothing to compress

        # Phase 3: Generate structured summary via LLM
        summary = self._generate_summary(agent, middle)

        # Phase 4: Assemble compressed messages
        compressed = []

        # Add head messages
        compressed.extend(head)

        # Add summary message (role chosen to avoid consecutive same-role violations)
        summary_role = "user" if (head and head[-1]["role"] == "assistant") else "assistant"
        compressed.append({
            "role": summary_role,
            "content": f"[Conversation Summary]\n{summary}",
        })

        # Add tail messages
        compressed.extend(tail)

        # Sanitize tool pairs (keep call/result together)
        compressed = self._sanitize_tool_pairs(compressed)

        # Update conversation history
        agent.conversation_history = compressed

        # Save as child session (new lineage)
        if not self.config.in_place:
            # Create new session ID for lineage tracking
            import uuid
            new_session_id = str(uuid.uuid4())
            agent.session_store.save_session(new_session_id, compressed)
            agent.session_id = new_session_id
        else:
            # In-place: save to same session
            agent._save_session()

    def _generate_summary(self, agent: AIAgent, middle_messages: list[dict]) -> str:
        """Generate structured summary using auxiliary LLM call."""
        # Build summary prompt
        conversation_text = self._format_messages_for_summary(middle_messages)

        summary_prompt = f"""Summarize the following conversation segment into a structured summary.

Format your response with these sections:
## Goal
What was the user trying to accomplish?

## Progress
### Done
- Completed tasks/steps

### In Progress
- Ongoing work

## Decisions
Key decisions made, with rationale

## Relevant Files
Files created, modified, or referenced

## Next Steps
What should happen next

## Critical Context
Any information that must not be lost (credentials, configs, specific values, etc.)

Conversation:
{conversation_text}"""

        # Use agent's run_single_turn for compression (no history, no persistence)
        summary = agent.run_single_turn(
            summary_prompt,
            system_prompt="You are a conversation summarizer. Produce concise, structured summaries that preserve all critical information.",
        )

        return summary

    def _format_messages_for_summary(self, messages: list[dict]) -> str:
        """Format messages for summary prompt."""
        lines = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            if role == "tool":
                lines.append(f"[Tool Result: {msg.get('tool_call_id', 'unknown')}]\n{content}")
            elif role == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    lines.append(f"[Tool Call: {tc['function']['name']}]\n{tc['function']['arguments']}")
            else:
                lines.append(f"[{role.upper()}]\n{content}")
        return "\n\n---\n\n".join(lines)

    def _sanitize_tool_pairs(self, messages: list[dict]) -> list[dict]:
        """
        Ensure tool calls and their results stay together.
        Remove orphaned tool calls or results.
        """
        result = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            if msg["role"] == "assistant" and msg.get("tool_calls"):
                # Check if all tool calls have results in subsequent messages
                tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
                found_results = set()

                # Look ahead for tool results
                j = i + 1
                while j < len(messages) and messages[j]["role"] == "tool":
                    found_results.add(messages[j]["tool_call_id"])
                    j += 1

                # Only keep if all tool calls have results
                if tool_call_ids.issubset(found_results):
                    result.append(msg)
                    # Add the tool results
                    k = i + 1
                    while k < j:
                        result.append(messages[k])
                        k += 1
                    i = j
                else:
                    # Orphaned tool calls - skip them
                    i += 1
            elif msg["role"] == "tool":
                # Orphaned tool result - skip
                i += 1
            else:
                result.append(msg)
                i += 1

        return result


# =============================================================================
# ContextEngine ABC (for plugins)
# =============================================================================

from abc import ABC, abstractmethod


class ContextEngine(ABC):
    """Pluggable context management interface."""

    @abstractmethod
    def should_compress(self, conversation_history: list[dict], model: str) -> bool:
        """Return True if compression should run."""
        pass

    @abstractmethod
    def compress(self, agent: AIAgent) -> None:
        """Compress the agent's conversation history."""
        pass

    @abstractmethod
    def estimate_tokens(self, messages: list[dict], model: str) -> int:
        """Estimate token count for messages."""
        pass


def get_default_context_engine() -> ContextEngine:
    """Get the default context engine."""
    return ContextCompressor()