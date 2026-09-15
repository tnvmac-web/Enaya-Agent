"""
Enaya Agent - Delegation Tools
delegate_task, subagent_status, subagent_steer, subagent_stop.
Enaya-specific tools for multi-agent orchestration.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, TYPE_CHECKING

from enaya.tools.registry import registry

if TYPE_CHECKING:
    from enaya.run_agent import create_agent, AIAgent, AgentConfig


# =============================================================================
# delegate_task
# =============================================================================

DELEGATE_TASK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "delegate_task",
        "description": "Delegate a complex task to a subagent with isolated context. Returns the subagent's final result.",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The task description for the subagent"},
                "context": {"type": "string", "description": "Background context the subagent needs (file paths, error messages, constraints)"},
                "model": {"type": "string", "description": "Model for subagent (default: same as parent)"},
                "max_iterations": {"type": "integer", "description": "Max iterations for subagent (default: 50)", "default": 50},
                "toolsets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Toolsets to enable for subagent (default: all parent toolsets)",
                },
            },
            "required": ["task", "context"],
        },
    },
}


def check_delegate_task_requirements() -> bool:
    return True


def delegate_task_tool(
    task: str,
    context: str,
    model: str = None,
    max_iterations: int = 50,
    toolsets: list[str] = None,
) -> str:
    """Spawn a subagent to handle a delegated task."""
    try:
        # Create subagent config
        subagent_config = AgentConfig(
            model=model or "openrouter:anthropic/claude-3.5-sonnet",
            max_turns=max_iterations,
            toolsets=toolsets or ["core", "research", "planning", "delegation", "synthesis"],
            profile="default",
            platform="subagent",
            chat_type="delegation",
            chat_id=str(uuid.uuid4())[:8],
        )

        subagent = AIAgent(subagent_config)

        # Build prompt with context
        prompt = f"""[DELEGATED SUBAGENT TASK]

Task: {task}

Context:
{context}

You are a subagent with isolated context. Complete this task and return your final result.
Think step by step. Use tools as needed. Provide a thorough response with findings, code, or deliverables as appropriate.
"""

        result = subagent.run_conversation(prompt)

        return json.dumps({
            "success": True,
            "subagent_id": subagent.session_id,
            "result": result,
        })

    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="delegate_task",
    toolset="delegation",
    schema=DELEGATE_TASK_SCHEMA,
    handler=delegate_task_tool,
    check_fn=check_delegate_task_requirements,
)


# =============================================================================
# subagent_status
# =============================================================================

SUBAGENT_STATUS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "subagent_status",
        "description": "Get status of running subagents.",
        "parameters": {
            "type": "object",
            "properties": {
                "subagent_id": {"type": "string", "description": "Specific subagent ID to check (optional)"},
            },
            "required": [],
        },
    },
}


def check_subagent_status_requirements() -> bool:
    return True


# Track active subagents (in memory - for demo)
_active_subagents: dict = {}


def subagent_status_tool(subagent_id: str = None) -> str:
    """Get status of subagents."""
    try:
        if subagent_id:
            if subagent_id in _active_subagents:
                return json.dumps({"subagent": _active_subagents[subagent_id]})
            else:
                return json.dumps({"error": f"Subagent not found: {subagent_id}"})
        else:
            return json.dumps({"subagents": list(_active_subagents.values())})
    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="subagent_status",
    toolset="delegation",
    schema=SUBAGENT_STATUS_SCHEMA,
    handler=subagent_status_tool,
    check_fn=check_subagent_status_requirements,
)


# =============================================================================
# subagent_steer
# =============================================================================

SUBAGENT_STEER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "subagent_steer",
        "description": "Send guidance to a running subagent.",
        "parameters": {
            "type": "object",
            "properties": {
                "subagent_id": {"type": "string", "description": "Subagent ID to steer"},
                "message": {"type": "string", "description": "Guidance message"},
            },
            "required": ["subagent_id", "message"],
        },
    },
}


def check_subagent_steer_requirements() -> bool:
    return True


def subagent_steer_tool(subagent_id: str, message: str) -> str:
    """Steer a running subagent."""
    try:
        # In a real implementation, this would communicate with the running subagent
        # For now, just log the steer message
        if subagent_id in _active_subagents:
            _active_subagents[subagent_id]["steer_messages"] = _active_subagents[subagent_id].get("steer_messages", [])
            _active_subagents[subagent_id]["steer_messages"].append(message)
            return json.dumps({"success": True, "message": "Steer message queued"})
        else:
            return json.dumps({"error": f"Subagent not found: {subagent_id}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="subagent_steer",
    toolset="delegation",
    schema=SUBAGENT_STEER_SCHEMA,
    handler=subagent_steer_tool,
    check_fn=check_subagent_steer_requirements,
)


# =============================================================================
# subagent_stop
# =============================================================================

SUBAGENT_STOP_SCHEMA = {
    "type": "function",
    "function": {
        "name": "subagent_stop",
        "description": "Stop a running subagent.",
        "parameters": {
            "type": "object",
            "properties": {
                "subagent_id": {"type": "string", "description": "Subagent ID to stop"},
            },
            "required": ["subagent_id"],
        },
    },
}


def check_subagent_stop_requirements() -> bool:
    return True


def subagent_stop_tool(subagent_id: str) -> str:
    """Stop a running subagent."""
    try:
        if subagent_id in _active_subagents:
            _active_subagents[subagent_id]["status"] = "stopped"
            return json.dumps({"success": True, "message": f"Subagent {subagent_id} stopped"})
        else:
            return json.dumps({"error": f"Subagent not found: {subagent_id}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="subagent_stop",
    toolset="delegation",
    schema=SUBAGENT_STOP_SCHEMA,
    handler=subagent_stop_tool,
    check_fn=check_subagent_stop_requirements,
)