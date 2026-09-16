#!/usr/bin/env python3
"""
Enaya Agent - Terminal Tool
Execute shell commands.
"""

from __future__ import annotations

import json
import subprocess
import os
import sys
from typing import Any

from enaya.tools.registry import registry


# =============================================================================
# Terminal Tool
# =============================================================================

TERMINAL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "terminal",
        "description": "Execute shell commands. Use for running commands, scripts, and system operations.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "cwd": {"type": "string", "description": "Working directory (default: current directory)"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)", "default": 60},
                "shell": {"type": "boolean", "description": "Run in shell (default: true)", "default": True},
            },
            "required": ["command"],
        },
    },
}


def check_terminal_requirements() -> bool:
    return True


def terminal_tool(command: str, cwd: str = None, timeout: int = 60, shell: bool = True) -> str:
    """Execute a shell command."""
    try:
        workdir = cwd or os.getcwd()
        
        result = subprocess.run(
            command,
            shell=shell,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        return json.dumps({
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        })
        
    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "error": f"Command timed out after {timeout} seconds",
            "stdout": "",
            "stderr": "",
            "returncode": -1,
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "stdout": "",
            "stderr": "",
            "returncode": -1,
        })


registry.register(
    name="terminal",
    toolset="core",
    schema=TERMINAL_SCHEMA,
    handler=terminal_tool,
    check_fn=check_terminal_requirements,
)