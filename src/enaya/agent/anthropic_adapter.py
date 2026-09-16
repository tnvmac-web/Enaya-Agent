"""
Enaya Agent - Anthropic Adapter
Anthropic Messages API translation.
Mirrors Hermes Agent's agent/anthropic_adapter.py exactly.
"""

from __future__ import annotations

import json

from enaya.run_agent import AIAgent


def anthropic_messages_call(
    agent: AIAgent,
    messages: list[dict],
    *,
    stream: bool = False,
) -> dict:
    """
    Make an Anthropic Messages API call.
    Translates OpenAI-format messages to Anthropic format.
    """

    client = agent._get_client()

    # Convert messages to Anthropic format
    system_prompt = ""
    anthropic_messages = []

    for msg in messages:
        role = msg["role"]
        content = msg.get("content", "")

        if role == "system":
            system_prompt += content + "\n\n"
        elif role == "user":
            if isinstance(content, list):
                # Handle cached content blocks
                for block in content:
                    if block.get("type") == "text":
                        anthropic_messages.append({"role": "user", "content": block["text"]})
            else:
                anthropic_messages.append({"role": "user", "content": content})
        elif role == "assistant":
            if msg.get("tool_calls"):
                # Assistant with tool calls
                for tc in msg["tool_calls"]:
                    anthropic_messages.append(
                        {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": tc["id"],
                                    "name": tc["function"]["name"],
                                    "input": json.loads(tc["function"]["arguments"]),
                                }
                            ],
                        }
                    )
            else:
                anthropic_messages.append({"role": "assistant", "content": content})
        elif role == "tool":
            anthropic_messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg["tool_call_id"],
                            "content": content,
                        }
                    ],
                }
            )

    # Build request
    kwargs = {
        "model": agent.model,
        "messages": anthropic_messages,
        "max_tokens": 8192,
        "temperature": agent.config.temperature,
        "top_p": agent.config.top_p,
    }

    if system_prompt:
        kwargs["system"] = system_prompt.strip()

    # Add tools if available
    tool_schemas = collect_anthropic_tool_schemas(
        agent.config.toolsets, agent.config.disabled_tools
    )
    if tool_schemas:
        kwargs["tools"] = tool_schemas

    if stream:
        return _stream_anthropic(client, kwargs)
    else:
        return _non_stream_anthropic(client, kwargs)


def collect_anthropic_tool_schemas(toolsets: list[str], disabled_tools: list[str]) -> list[dict]:
    """Convert tool schemas to Anthropic format."""
    from enaya.tools.registry import registry

    schemas = []
    for toolset in toolsets:
        for name in registry.get_toolset(toolset):
            if name in disabled_tools:
                continue
            tool = registry.get(name)
            if tool and tool.check_fn():
                fn_schema = tool.schema.get("function", {})
                schemas.append(
                    {
                        "name": fn_schema.get("name"),
                        "description": fn_schema.get("description"),
                        "input_schema": fn_schema.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    }
                )
    return schemas


def _non_stream_anthropic(client, kwargs: dict) -> dict:
    """Non-streaming Anthropic call."""
    response = client.messages.create(**kwargs)

    result = {"content": "", "tool_calls": []}

    for block in response.content:
        if block.type == "text":
            result["content"] += block.text
        elif block.type == "tool_use":
            result["tool_calls"].append(
                {
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                }
            )

    result["usage"] = {
        "prompt_tokens": response.usage.input_tokens,
        "completion_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
    }
    result["finish_reason"] = response.stop_reason

    return result


def _stream_anthropic(client, kwargs: dict) -> dict:
    """Streaming Anthropic call."""
    # Simplified - real implementation would handle streaming events
    return {"content": "", "tool_calls": []}


# =============================================================================
# Prompt Caching Helpers
# =============================================================================


def apply_anthropic_caching(messages: list[dict], cache_ttl: str = "5m") -> list[dict]:
    """Apply Anthropic cache_control markers."""
    # Anthropic uses cache_control on content blocks
    non_system_indices = [i for i, m in enumerate(messages) if m["role"] != "system"]

    # System prompt (always cached)
    if messages and messages[0]["role"] == "system":
        content = messages[0]["content"]
        if isinstance(content, str):
            messages[0]["content"] = [
                {
                    "type": "text",
                    "text": content,
                    "cache_control": {"type": "ephemeral", "ttl": cache_ttl},
                }
            ]

    # Last 3 non-system messages
    if len(non_system_indices) >= 3:
        for idx in [-3, -2, -1]:
            msg_idx = non_system_indices[idx]
            content = messages[msg_idx]["content"]
            if isinstance(content, str):
                messages[msg_idx]["content"] = [
                    {
                        "type": "text",
                        "text": content,
                        "cache_control": {"type": "ephemeral", "ttl": cache_ttl},
                    }
                ]

    return messages
