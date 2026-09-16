#!/usr/bin/env python3
"""
Enaya Agent - Task-delegation AI agent with multi-agent orchestration.

AIAgent facade — public entry points for CLI, gateway, ACP, batch, and library use.
Mirrors Hermes Agent's run_agent.py architecture exactly.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from enaya.agent.context_compressor import ContextCompressor
from enaya.agent.prompt_builder import build_system_prompt
from enaya.cli.runtime_provider import resolve_runtime_provider
from enaya.hermes_state import SessionStore
from enaya.model_tools import collect_tool_schemas, handle_function_call
from enaya.tools.registry import discover_builtin_tools

if TYPE_CHECKING:
    pass


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass
class AgentConfig:
    """Configuration for AIAgent instance."""

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
    chat_type: str = "private"
    chat_id: str = "local"


# =============================================================================
# Callback Types
# =============================================================================

ToolProgressCallback = Callable[[str, str, bool], None]  # tool_name, status, is_start
ThinkingCallback = Callable[[bool], None]  # is_thinking
ReasoningCallback = Callable[[str], None]  # reasoning_content
ClarifyCallback = Callable[[str, list[dict]], str]  # question, choices -> answer
StepCallback = Callable[[dict], None]  # step_info
StreamDeltaCallback = Callable[[str], None]  # delta
ToolGenCallback = Callable[[dict], None]  # tool_call
StatusCallback = Callable[[str], None]  # status_message


# =============================================================================
# AIAgent - Main Facade
# =============================================================================


class AIAgent:
    """
    Main agent facade. One class serves all entry points (CLI, gateway, ACP, batch, API server).
    Platform differences live in entry points, not the agent core.
    """

    def __init__(
        self,
        config: AgentConfig,
        *,
        tool_progress_callback: ToolProgressCallback | None = None,
        thinking_callback: ThinkingCallback | None = None,
        reasoning_callback: ReasoningCallback | None = None,
        clarify_callback: ClarifyCallback | None = None,
        step_callback: StepCallback | None = None,
        stream_delta_callback: StreamDeltaCallback | None = None,
        tool_gen_callback: ToolGenCallback | None = None,
        status_callback: StatusCallback | None = None,
        approval_callback: Callable[[str, dict], bool] | None = None,
    ):
        self.config = config
        self.tool_progress_callback = tool_progress_callback
        self.thinking_callback = thinking_callback
        self.reasoning_callback = reasoning_callback
        self.clarify_callback = clarify_callback
        self.step_callback = step_callback
        self.stream_delta_callback = stream_delta_callback
        self.tool_gen_callback = tool_gen_callback
        self.status_callback = status_callback
        self.approval_callback = approval_callback

        # Resolve provider at init time
        self._runtime = resolve_runtime_provider(
            provider=config.provider,
            model=config.model,
            base_url=config.base_url,
            api_key=config.api_key,
        )
        self.provider = self._runtime.provider
        self.model = self._runtime.model
        self.base_url = self._runtime.base_url
        self.api_key = self._runtime.api_key
        self.api_mode = self._runtime.api_mode
        self._client = None
        self._client_kwargs = {}

        # Session management
        self.session_id = config.session_id or str(uuid.uuid4())
        self.session_store = SessionStore(profile=config.profile)
        self.conversation_history: list[dict] = []
        self._system_prompt_cached: str | None = None
        self._system_prompt_hash: str | None = None

        # Compression
        self.compressor = ContextCompressor(
            threshold=config.compression_threshold,
            protect_last_n=config.compression_protect_last_n,
        )

        # State
        self._fallback_activated = False
        self._iteration_count = 0
        self._interrupted = False

        # Discover built-in tools
        discover_builtin_tools()

    # -------------------------------------------------------------------------
    # Public Entry Points
    # -------------------------------------------------------------------------

    def run_conversation(
        self,
        user_input: str,
        *,
        session_id: str | None = None,
        resume: bool = False,
        prefill: str | None = None,
        ephemeral_system_prompt: str | None = None,
    ) -> str:
        """
        Run a full conversation turn (or multiple turns with tool calling).
        Used by CLI, gateway, cron, ACP.
        """
        from enaya.agent.conversation_loop import run_conversation

        if session_id:
            self.session_id = session_id

        if resume:
            self._load_session()

        return run_conversation(
            self, user_input, prefill=prefill, ephemeral_system_prompt=ephemeral_system_prompt
        )

    def run_single_turn(
        self,
        user_input: str,
        *,
        system_prompt: str | None = None,
        prefill: str | None = None,
    ) -> str:
        """
        Run a single turn without history, persistence, or compression.
        Used by auxiliary tasks (vision, compression, web extraction).
        """
        # Build minimal prompt
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_input})

        # Make API call
        response = self._make_api_call(messages)
        return response.get("content", "")

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    def _load_session(self) -> None:
        """Load conversation history from session store."""
        self.conversation_history = self.session_store.load_session(self.session_id) or []

    def _save_session(self) -> None:
        """Save conversation history to session store."""
        self.session_store.save_session(self.session_id, self.conversation_history)

    def _flush_memory(self) -> None:
        """Flush memory changes to disk."""
        # Memory is handled by the memory tool interception
        pass

    # -------------------------------------------------------------------------
    # Prompt Building
    # -------------------------------------------------------------------------

    def get_system_prompt(self, *, force_rebuild: bool = False) -> str:
        """Get or build the cached system prompt."""
        if self._system_prompt_cached and not force_rebuild:
            return self._system_prompt_cached

        self._system_prompt_cached = build_system_prompt(
            agent=self,
            tool_schemas=collect_tool_schemas(self.config.toolsets, self.config.disabled_tools),
        )
        return self._system_prompt_cached

    # -------------------------------------------------------------------------
    # API Calls
    # -------------------------------------------------------------------------

    def _make_api_call(self, messages: list[dict], *, stream: bool = False) -> dict:
        """Make an interruptible API call based on api_mode."""
        if self.api_mode == "chat_completions":
            return self._chat_completions_call(messages, stream=stream)
        elif self.api_mode == "codex_responses":
            return self._codex_responses_call(messages, stream=stream)
        elif self.api_mode == "anthropic_messages":
            return self._anthropic_messages_call(messages, stream=stream)
        else:
            raise ValueError(f"Unknown api_mode: {self.api_mode}")

    def _chat_completions_call(self, messages: list[dict], *, stream: bool = False) -> dict:
        """OpenAI Chat Completions format."""

        client = self._get_client()
        kwargs = self._build_api_kwargs(messages, stream=stream)

        if stream:
            return self._stream_chat_completions(client, kwargs)
        else:
            response = client.chat.completions.create(**kwargs)
            return self._parse_chat_completions_response(response)

    def _codex_responses_call(self, messages: list[dict], *, stream: bool = False) -> dict:
        """OpenAI Responses API (stateful)."""

        client = self._get_client()
        kwargs = self._build_responses_kwargs(messages, stream=stream)

        if stream:
            return self._stream_responses(client, kwargs)
        else:
            response = client.responses.create(**kwargs)
            return self._parse_responses_response(response)

    def _anthropic_messages_call(self, messages: list[dict], *, stream: bool = False) -> dict:
        """Anthropic Messages API via adapter."""
        from enaya.agent.anthropic_adapter import anthropic_messages_call

        return anthropic_messages_call(self, messages, stream=stream)

    def _get_client(self):
        """Get or create the API client."""
        if self._client is None:
            if self.api_mode in ("chat_completions", "codex_responses"):
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    **self._client_kwargs,
                )
            elif self.api_mode == "anthropic_messages":
                import anthropic

                self._client = anthropic.Anthropic(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
        return self._client

    def _build_api_kwargs(self, messages: list[dict], *, stream: bool = False) -> dict:
        """Build kwargs for chat_completions call."""
        tool_schemas = collect_tool_schemas(self.config.toolsets, self.config.disabled_tools)
        kwargs = {
            "model": self.model,
            "messages": messages,
            "tools": tool_schemas if tool_schemas else None,
            "tool_choice": "auto" if tool_schemas else None,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "stream": stream,
        }
        if self.api_mode == "codex_responses":
            # Responses API uses different format
            pass
        return kwargs

    def _build_responses_kwargs(self, messages: list[dict], *, stream: bool = False) -> dict:
        """Build kwargs for Responses API call."""
        tool_schemas = collect_tool_schemas(self.config.toolsets, self.config.disabled_tools)
        # Convert messages to Responses API input format
        input_items = self._convert_to_responses_input(messages)
        return {
            "model": self.model,
            "input": input_items,
            "tools": tool_schemas if tool_schemas else None,
            "tool_choice": "auto" if tool_schemas else None,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "stream": stream,
        }

    def _convert_to_responses_input(self, messages: list[dict]) -> list[dict]:
        """Convert OpenAI-format messages to Responses API input items."""
        # Simplified conversion - real implementation handles all message types
        input_items = []
        for msg in messages:
            if msg["role"] == "system":
                input_items.append({"type": "message", "role": "system", "content": msg["content"]})
            elif msg["role"] == "user":
                input_items.append({"type": "message", "role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        input_items.append(
                            {
                                "type": "function_call",
                                "call_id": tc["id"],
                                "name": tc["function"]["name"],
                                "arguments": tc["function"]["arguments"],
                            }
                        )
                else:
                    input_items.append(
                        {"type": "message", "role": "assistant", "content": msg["content"]}
                    )
            elif msg["role"] == "tool":
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": msg["tool_call_id"],
                        "output": msg["content"],
                    }
                )
        return input_items

    def _parse_chat_completions_response(self, response) -> dict:
        """Parse OpenAI Chat Completions response."""
        # Handle None or empty response
        if not response or not response.choices:
            return {
                "content": "",
                "tool_calls": [],
                "finish_reason": "error",
                "error": "Empty or invalid response from API",
            }

        choice = response.choices[0]
        result = {"content": choice.message.content or ""}
        if choice.message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]
        if hasattr(response, "usage") and response.usage:
            result["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        result["finish_reason"] = choice.finish_reason
        return result

    def _parse_responses_response(self, response) -> dict:
        """Parse OpenAI Responses API response."""
        result = {"content": "", "tool_calls": []}
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        result["content"] += content.text
            elif item.type == "function_call":
                result["tool_calls"].append(
                    {
                        "id": item.call_id,
                        "type": "function",
                        "function": {
                            "name": item.name,
                            "arguments": json.dumps(item.arguments)
                            if isinstance(item.arguments, dict)
                            else item.arguments,
                        },
                    }
                )
        if hasattr(response, "usage") and response.usage:
            result["usage"] = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        result["finish_reason"] = getattr(response, "status", "completed")
        return result

    def _stream_chat_completions(self, client, kwargs: dict) -> dict:
        """Stream chat completions and accumulate."""
        full_content = ""
        tool_calls: dict[int, dict] = {}

        stream = client.chat.completions.create(**kwargs)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                full_content += delta.content
                if self.stream_delta_callback:
                    self.stream_delta_callback(delta.content)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc.id:
                        tool_calls[idx]["id"] = tc.id
                    if tc.function.name:
                        tool_calls[idx]["function"]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls[idx]["function"]["arguments"] += tc.function.arguments

        result = {"content": full_content}
        if tool_calls:
            result["tool_calls"] = list(tool_calls.values())
        return result

    def _stream_responses(self, client, kwargs: dict) -> dict:
        """Stream Responses API and accumulate."""
        # Simplified - real implementation handles streaming events
        return {"content": "", "tool_calls": []}

    # -------------------------------------------------------------------------
    # Tool Execution (delegated to conversation_loop)
    # -------------------------------------------------------------------------

    def execute_tool(self, tool_call: dict, task_id: str) -> str:
        """Execute a single tool call. Called from conversation_loop."""
        return handle_function_call(
            tool_call,
            toolsets=self.config.toolsets,
            disabled_tools=self.config.disabled_tools,
            task_id=task_id,
            approval_callback=self.approval_callback,
            progress_callback=self.tool_progress_callback,
        )

    # -------------------------------------------------------------------------
    # Compression
    # -------------------------------------------------------------------------

    def maybe_compress(self) -> bool:
        """Check if compression needed and run it."""
        if self.compressor.should_compress(self.conversation_history, self.model):
            self.compressor.compress(self)
            return True
        return False

    # -------------------------------------------------------------------------
    # Interrupt Handling
    # -------------------------------------------------------------------------

    def interrupt(self) -> None:
        """Signal the agent to interrupt current operation."""
        self._interrupted = True

    def is_interrupted(self) -> bool:
        return self._interrupted

    # -------------------------------------------------------------------------
    # Fallback
    # -------------------------------------------------------------------------

    def try_fallback(self) -> bool:
        """Attempt to activate fallback provider."""
        if self._fallback_activated or not self.config.fallback_providers:
            return False

        for fb_provider, fb_model in self.config.fallback_providers:
            try:
                new_runtime = resolve_runtime_provider(
                    provider=fb_provider,
                    model=fb_model,
                )
                self.provider = new_runtime.provider
                self.model = new_runtime.model
                self.base_url = new_runtime.base_url
                self.api_key = new_runtime.api_key
                self.api_mode = new_runtime.api_mode
                self._client = None
                self._client_kwargs = {}
                self._system_prompt_cached = None  # Force rebuild
                self._fallback_activated = True
                if self.status_callback:
                    self.status_callback(f"Fallback activated: {fb_provider}/{fb_model}")
                return True
            except Exception:
                continue
        return False


# =============================================================================
# High-Level Convenience Functions
# =============================================================================


def create_agent(
    model: str = "openrouter:anthropic/claude-sonnet-4",
    provider: str | None = None,
    **kwargs,
) -> AIAgent:
    """Create an AIAgent with sensible defaults."""
    config = AgentConfig(model=model, provider=provider, **kwargs)
    return AIAgent(config)


async def run_agent_async(
    prompt: str,
    model: str = "openrouter:anthropic/claude-sonnet-4",
    **kwargs,
) -> str:
    """Async wrapper for run_conversation."""
    agent = create_agent(model=model, **kwargs)
    return agent.run_conversation(prompt)


# =============================================================================
# Batch/Headless Execution
# =============================================================================


class BatchRunner:
    """Run multiple prompts in batch/headless mode."""

    def __init__(self, agent: AIAgent):
        self.agent = agent

    def run(self, prompts: list[str]) -> list[str]:
        results = []
        for prompt in prompts:
            try:
                result = self.agent.run_conversation(prompt)
                results.append(result)
            except Exception as e:
                results.append(f"Error: {e}")
        return results


if __name__ == "__main__":
    # Smoke test
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--query", default="Hello, Enaya!")
    args = parser.parse_args()

    agent = create_agent()
    print(agent.run_conversation(args.query))
