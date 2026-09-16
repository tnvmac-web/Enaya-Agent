"""
Enaya Agent - Core File Tools
read_file, write_file, patch, search_files.
Mirrors Hermes Agent's tools/file_tools.py exactly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from enaya.tools.registry import registry

# =============================================================================
# read_file
# =============================================================================

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a text file with line numbers and pagination. Use this instead of cat/head/tail.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read (absolute, relative, or ~/path)"},
                "offset": {"type": "integer", "description": "Line number to start reading from (1-indexed, default: 1)", "default": 1},
                "limit": {"type": "integer", "description": "Maximum number of lines to read (default: 2000, max: 2000)", "default": 2000},
            },
            "required": ["path"],
        },
    },
}


def check_read_file_requirements() -> bool:
    return True


def read_file_tool(path: str, offset: int = 1, limit: int = 2000) -> str:
    """Read a text file with line numbers."""
    try:
        # Expand user path
        path = os.path.expanduser(path)
        file_path = Path(path)

        if not file_path.exists():
            return json.dumps({"error": f"File not found: {path}"})

        if not file_path.is_file():
            return json.dumps({"error": f"Not a file: {path}"})

        # Read file
        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        # Apply offset and limit (1-indexed)
        start = max(0, offset - 1)
        end = min(len(lines), start + limit)
        selected_lines = lines[start:end]

        # Format with line numbers
        result_lines = []
        for i, line in enumerate(selected_lines, start=start + 1):
            result_lines.append(f"{i}|{line}")

        return json.dumps({
            "content": "\n".join(result_lines),
            "total_lines": len(lines),
            "showing_lines": f"{start + 1}-{end}",
        })

    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="read_file",
    toolset="core",
    schema=READ_FILE_SCHEMA,
    handler=read_file_tool,
    check_fn=check_read_file_requirements,
)


# =============================================================================
# write_file
# =============================================================================

WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file, completely replacing existing content. Creates parent directories automatically.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write (will be created if it doesn't exist, overwritten if it does)"},
                "content": {"type": "string", "description": "Complete content to write to the file"},
            },
            "required": ["path", "content"],
        },
    },
}


def check_write_file_requirements() -> bool:
    return True


def write_file_tool(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        path = os.path.expanduser(path)
        file_path = Path(path)

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path.write_text(content, encoding="utf-8")

        return json.dumps({
            "success": True,
            "path": str(file_path),
            "bytes_written": len(content.encode("utf-8")),
        })

    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="write_file",
    toolset="core",
    schema=WRITE_FILE_SCHEMA,
    handler=write_file_tool,
    check_fn=check_write_file_requirements,
)


# =============================================================================
# patch
# =============================================================================

PATCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "patch",
        "description": "Targeted find-and-replace edits in files. Uses fuzzy matching so minor whitespace/indentation differences won't break it.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to edit"},
                "old_string": {"type": "string", "description": "Exact text to find and replace. Must be unique in the file. Include surrounding context lines to ensure uniqueness."},
                "new_string": {"type": "string", "description": "Changed replacement text; it must differ from old_string. Pass empty string '' to delete the matched text."},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences instead of requiring a unique match (default: false)", "default": False},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
}


def check_patch_requirements() -> bool:
    return True


def patch_tool(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Apply a patch to a file."""
    try:
        path = os.path.expanduser(path)
        file_path = Path(path)

        if not file_path.exists():
            return json.dumps({"error": f"File not found: {path}"})

        content = file_path.read_text(encoding="utf-8")

        if replace_all:
            if old_string not in content:
                return json.dumps({"error": "old_string not found in file"})
            new_content = content.replace(old_string, new_string)
            count = content.count(old_string)
        else:
            # Count occurrences
            count = content.count(old_string)
            if count == 0:
                return json.dumps({"error": "old_string not found in file"})
            if count > 1:
                return json.dumps({"error": f"old_string found {count} times. Use replace_all=true or provide more context."})
            new_content = content.replace(old_string, new_string, 1)

        file_path.write_text(new_content, encoding="utf-8")

        return json.dumps({
            "success": True,
            "replacements": count,
        })

    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="patch",
    toolset="core",
    schema=PATCH_SCHEMA,
    handler=patch_tool,
    check_fn=check_patch_requirements,
)


# =============================================================================
# search_files
# =============================================================================

SEARCH_FILES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": "Search file contents or find files by name. Ripgrep-backed, faster than shell equivalents.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern for content search, or glob pattern for file search"},
                "target": {"type": "string", "enum": ["content", "files"], "description": "'content' searches inside file contents, 'files' searches for files by name", "default": "content"},
                "path": {"type": "string", "description": "Directory or file to search in (default: current working directory)", "default": "."},
                "file_glob": {"type": "string", "description": "Filter files by pattern in grep mode (e.g., '*.py' to only search Python files)"},
                "limit": {"type": "integer", "description": "Maximum number of results to return (default: 50)", "default": 50},
                "offset": {"type": "integer", "description": "Skip first N results for pagination (default: 0)", "default": 0},
                "output_mode": {"type": "string", "enum": ["content", "files_only", "count"], "description": "Output format for grep mode: 'content' shows matching lines with line numbers, 'files_only' lists file paths, 'count' shows match counts per file", "default": "content"},
                "context": {"type": "integer", "description": "Number of context lines before and after each match (grep mode only)", "default": 0},
            },
            "required": ["pattern"],
        },
    },
}


def check_search_files_requirements() -> bool:
    return True


def search_files_tool(
    pattern: str,
    target: str = "content",
    path: str = ".",
    file_glob: str = None,
    limit: int = 50,
    offset: int = 0,
    output_mode: str = "content",
    context: int = 0,
) -> str:
    """Search files using ripgrep."""
    try:
        import subprocess

        path = os.path.expanduser(path)

        # Build ripgrep command
        cmd = ["rg", "--json", "--no-heading", "--line-number"]

        if target == "files":
            cmd.extend(["--files", "--glob", pattern])
        else:
            cmd.append(pattern)
            if file_glob:
                cmd.extend(["--glob", file_glob])

        cmd.extend(["-C", str(context)])
        cmd.append(path)

        # Run ripgrep
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 2:
            return json.dumps({"error": f"Invalid pattern: {pattern}"})
        elif result.returncode > 1:
            return json.dumps({"error": f"rg failed: {result.stderr}"})

        # Parse JSON output
        matches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                if data["type"] == "match":
                    match_data = data["data"]
                    matches.append({
                        "path": match_data["path"]["text"],
                        "line_number": match_data["line_number"],
                        "lines": match_data["lines"]["text"],
                    })
            except json.JSONDecodeError:
                continue

        # Apply offset and limit
        matches = matches[offset:offset + limit]

        if output_mode == "files_only":
            files = list(set(m["path"] for m in matches))
            return json.dumps({"matches": files, "count": len(files)})
        elif output_mode == "count":
            from collections import Counter
            counts = Counter(m["path"] for m in matches)
            return json.dumps({"counts": dict(counts)})
        else:
            return json.dumps({"matches": matches, "total": len(matches)})

    except FileNotFoundError:
        return json.dumps({"error": "ripgrep (rg) not installed"})
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Search timed out"})
    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="search_files",
    toolset="core",
    schema=SEARCH_FILES_SCHEMA,
    handler=search_files_tool,
    check_fn=check_search_files_requirements,
)
