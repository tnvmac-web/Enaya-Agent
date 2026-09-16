"""
Enaya Agent - Model Tools
Tool schema collection and handle_function_call() dispatch.
Mirrors Hermes Agent's model_tools.py exactly.
"""

from __future__ import annotations

from enaya.tools.registry import registry


def collect_tool_schemas(toolsets: list[str], disabled_tools: list[str]) -> list[dict]:
    """
    Collect OpenAI-compatible tool schemas for given toolsets.
    Returns list of function schemas for API calls.
    """
    return registry.get_schemas(toolsets, disabled_tools)


def handle_function_call(
    tool_call: dict,
    toolsets: list[str],
    disabled_tools: list[str],
    task_id: str,
    approval_callback: callable | None = None,
    progress_callback: callable | None = None,
) -> str:
    """
    Main tool dispatch function.
    Called from conversation_loop when tool_calls are present.
    """
    return registry.dispatch(
        tool_call,
        toolsets=toolsets,
        disabled_tools=disabled_tools,
        task_id=task_id,
        approval_callback=approval_callback,
        progress_callback=progress_callback,
    )


# =============================================================================
# Agent-Level Tool Interception
# These tools are intercepted by the agent loop before reaching the registry
# =============================================================================

AGENT_LEVEL_TOOLS = {
    "todo",
    "memory",
    "session_search",
    "delegate_task",
}


def is_agent_level_tool(name: str) -> bool:
    """Check if tool is handled at agent level."""
    return name in AGENT_LEVEL_TOOLS


# =============================================================================
# Tool Schema Builders (for common patterns)
# =============================================================================

def build_function_schema(
    name: str,
    description: str,
    parameters: dict,
    required: list[str] = None,
) -> dict:
    """Build a standard OpenAI function schema."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required or [],
            },
        },
    }


def string_param(description: str) -> dict:
    return {"type": "string", "description": description}


def integer_param(description: str, minimum: int = None, maximum: int = None) -> dict:
    param = {"type": "integer", "description": description}
    if minimum is not None:
        param["minimum"] = minimum
    if maximum is not None:
        param["maximum"] = maximum
    return param


def boolean_param(description: str) -> dict:
    return {"type": "boolean", "description": description}


def array_param(description: str, items: dict) -> dict:
    return {"type": "array", "description": description, "items": items}


def object_param(description: str, properties: dict, required: list[str] = None) -> dict:
    param = {"type": "object", "description": description, "properties": properties}
    if required:
        param["required"] = required
    return param
