"""
Enaya Agent - Tool Registry
Central tool registry (no deps, imported by all tool files).
Mirrors Hermes Agent's tools/registry.py exactly.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class ToolDef:
    name: str
    toolset: str
    schema: dict
    handler: Callable
    check_fn: Callable[[], bool]
    is_async: bool = False


class ToolRegistry:
    """Central tool registry. Auto-discovers tools at import time."""

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}
        self._toolsets: dict[str, list[str]] = {}
        self._discovered = False

    def register(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Callable[[], bool],
        is_async: bool = False,
    ) -> None:
        """Register a tool. Called at module import time."""
        if name in self._tools:
            # Allow override (plugins can override built-ins)
            pass

        self._tools[name] = ToolDef(
            name=name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            is_async=is_async,
        )

        if toolset not in self._toolsets:
            self._toolsets[toolset] = []
        if name not in self._toolsets[toolset]:
            self._toolsets[toolset].append(name)

    def get(self, name: str) -> ToolDef | None:
        """Get tool definition by name."""
        return self._tools.get(name)

    def get_toolset(self, toolset: str) -> list[str]:
        """Get list of tool names in a toolset."""
        return self._toolsets.get(toolset, [])

    def get_all_tools(self) -> dict[str, ToolDef]:
        """Get all registered tools."""
        return self._tools.copy()

    def get_schemas(self, toolsets: list[str], disabled_tools: list[str]) -> list[dict]:
        """Get schemas for tools in given toolsets, excluding disabled."""
        schemas = []
        for toolset in toolsets:
            for name in self.get_toolset(toolset):
                if name in disabled_tools:
                    continue
                tool = self._tools.get(name)
                if tool and tool.check_fn():
                    schemas.append(tool.schema)
        return schemas

    def dispatch(
        self,
        tool_call: dict,
        toolsets: list[str],
        disabled_tools: list[str],
        task_id: str,
        approval_callback: Callable | None = None,
        progress_callback: Callable | None = None,
    ) -> str:
        """
        Dispatch a tool call to its handler.
        Returns JSON string result.
        """
        name = tool_call.get("function", {}).get("name")
        if not name:
            return json.dumps({"error": "Missing tool name"})

        tool = self._tools.get(name)
        if not tool:
            return json.dumps({"error": f"Tool not found: {name}"})

        # Check if tool is in allowed toolsets
        if tool.toolset not in toolsets:
            return json.dumps({"error": f"Tool {name} not in allowed toolsets"})

        # Check if disabled
        if name in disabled_tools:
            return json.dumps({"error": f"Tool {name} is disabled"})

        # Check requirements
        if not tool.check_fn():
            return json.dumps({"error": f"Tool {name} requirements not met"})

        # Progress callback - start
        if progress_callback:
            progress_callback(name, "start", True)

        try:
            # Parse arguments
            args_str = tool_call.get("function", {}).get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}

            # Execute handler
            if tool.is_async:
                import asyncio
                result = asyncio.run(tool.handler(args, task_id=task_id))
            else:
                result = tool.handler(args, task_id=task_id)

            # Ensure result is JSON string
            if not isinstance(result, str):
                result = json.dumps(result)

        except Exception as e:
            result = json.dumps({"error": str(e)})

        # Progress callback - end
        if progress_callback:
            progress_callback(name, "complete", False)

        return result

    def discover_builtin_tools(self) -> None:
        """Discover built-in tools by importing tool modules."""
        if self._discovered:
            return

        # Import all tool modules to trigger registration
        # Order matters for dependencies
        try:
            # Enaya-specific tools
            from enaya.tools import (
                code_execution_tool,
                delegate_tool,
                delegation_tools,
                file_tools,
                mcp_tool,
                planning_tools,
                research_tools,
                synthesis_tools,
                terminal_tool,
                web_tools,
            )
        except ImportError:
            pass  # Tools not yet implemented

        self._discovered = True


# Global registry instance
registry = ToolRegistry()


def discover_builtin_tools() -> None:
    """Public function to trigger tool discovery."""
    registry.discover_builtin_tools()
