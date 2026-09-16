#!/usr/bin/env python3
"""
Enaya Agent - Code Execution Tool
Execute Python code in sandboxed environment.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

from enaya.tools.registry import registry

# =============================================================================
# Code Execution Tool
# =============================================================================

CODE_EXECUTION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_code",
        "description": (
            "Execute Python code in a sandboxed environment. Returns "
            "stdout, stderr, and return value."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds (default: 30)",
                    "default": 30,
                },
                "capture_output": {
                    "type": "boolean",
                    "description": "Capture stdout/stderr (default: true)",
                    "default": True,
                },
            },
            "required": ["code"],
        },
    },
}


def check_code_execution_requirements() -> bool:
    return True


def execute_code_tool(code: str, timeout: int = 30, capture_output: bool = True) -> str:
    """Execute Python code in a sandboxed subprocess."""
    try:
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix="enaya_exec_"
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Run the code in a subprocess
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir(),
            )

            return json.dumps(
                {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
            )

        except subprocess.TimeoutExpired:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Code execution timed out after {timeout} seconds",
                    "stdout": "",
                    "stderr": "",
                    "returncode": -1,
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                    "stdout": "",
                    "stderr": "",
                    "returncode": -1,
                }
            )
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except Exception:
                pass

    except Exception as e:
        return json.dumps({"success": False, "error": f"Failed to execute code: {str(e)}"})


registry.register(
    name="execute_code",
    toolset="core",
    schema=CODE_EXECUTION_SCHEMA,
    handler=execute_code_tool,
    check_fn=check_code_execution_requirements,
)
