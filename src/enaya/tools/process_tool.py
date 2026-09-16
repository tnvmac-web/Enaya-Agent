#!/usr/bin/env python3
"""
Enaya Agent - Process Tool
Manage background processes.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time

from enaya.tools.registry import registry

# =============================================================================
# Process Tool
# =============================================================================

PROCESS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "process",
        "description": "Manage background processes: start, stop, list, and monitor.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "stop", "list", "logs", "status"],
                    "description": "Action to perform",
                },
                "command": {"type": "string", "description": "Command to start (for start action)"},
                "pid": {
                    "type": "integer",
                    "description": "Process ID (for stop/logs/status actions)",
                },
                "name": {"type": "string", "description": "Process name (for start action)"},
                "cwd": {"type": "string", "description": "Working directory"},
            },
            "required": ["action"],
        },
    },
}


def check_process_requirements() -> bool:
    return True


# Global process registry
_processes: dict[int, dict] = {}


def process_tool(
    action: str, command: str = None, pid: int = None, name: str = None, cwd: str = None
) -> str:
    """Process management tool."""
    global _processes

    try:
        if action == "start":
            if not command:
                return json.dumps({"error": "command required for start action"})

            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd or os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )

            proc_info = {
                "pid": proc.pid,
                "command": command,
                "name": name or command[:50],
                "cwd": cwd or os.getcwd(),
                "started_at": time.time(),
                "process": proc,
            }
            _processes[proc.pid] = proc_info

            return json.dumps(
                {
                    "success": True,
                    "pid": proc.pid,
                    "message": f"Started process {proc.pid}: {command}",
                }
            )

        elif action == "stop":
            if pid is None:
                return json.dumps({"error": "pid required for stop action"})

            if pid not in _processes:
                return json.dumps({"error": f"Process {pid} not found"})

            proc_info = _processes[pid]
            proc = proc_info["process"]

            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=5)
            except Exception:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)

            del _processes[pid]
            return json.dumps({"success": True, "message": f"Stopped process {pid}"})

        elif action == "list":
            result = []
            for pid, info in _processes.items():
                result.append(
                    {
                        "pid": pid,
                        "name": info["name"],
                        "command": info["command"],
                        "running_time": time.time() - info["started_at"],
                    }
                )
            return json.dumps({"processes": result})

        elif action == "logs":
            if pid is None:
                return json.dumps({"error": "pid required for logs action"})

            if pid not in _processes:
                return json.dumps({"error": f"Process {pid} not found"})

            # For simplicity, return empty logs (real implementation would capture stdout/stderr)
            return json.dumps(
                {
                    "pid": pid,
                    "stdout": "Logs not captured in this implementation",
                    "stderr": "",
                }
            )

        elif action == "status":
            if pid is None:
                return json.dumps({"error": "pid required for status action"})

            if pid not in _processes:
                return json.dumps({"error": f"Process {pid} not found"})

            proc_info = _processes[pid]
            proc = proc_info["process"]

            return json.dumps(
                {
                    "pid": pid,
                    "name": proc_info["name"],
                    "running": proc.poll() is None,
                    "returncode": proc.poll(),
                    "running_time": time.time() - proc_info["started_at"],
                }
            )

        else:
            return json.dumps({"error": f"Unknown action: {action}"})

    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="process",
    toolset="core",
    schema={
        "type": "function",
        "function": {
            "name": "process",
            "description": "Manage background processes: start, stop, list, and monitor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["start", "stop", "list", "logs", "status"],
                    },
                    "command": {"type": "string"},
                    "pid": {"type": "integer"},
                    "name": {"type": "string"},
                    "cwd": {"type": "string"},
                },
                "required": ["action"],
            },
        },
    },
    handler=process_tool,
    check_fn=check_process_requirements,
)
