#!/usr/bin/env python3
"""
Enaya Agent - Tools Package
Core tools for the agent.
"""

from .delegation_tools import (
    delegate_task_tool,
    subagent_status_tool,
    subagent_steer_tool,
    subagent_stop_tool,
)

# Import and register all tools
from .file_tools import (
    patch_tool,
    read_file_tool,
    search_files_tool,
    write_file_tool,
)
from .planning_tools import (
    plan_create_tool,
    plan_review_tool,
    task_decompose_tool,
)
from .registry import ToolDef, registry
from .research_tools import (
    arxiv_search_tool,
    paper_analyze_tool,
    source_validator_tool,
)
from .synthesis_tools import (
    compare_sources_tool,
    extract_claims_tool,
    synthesize_results_tool,
)
from .web_tools import (
    web_extract_tool,
    web_search_tool,
)

# New tools (lazy-load via importlib)
try:
    import importlib.util

    if importlib.util.find_spec(".browser_cdp_tool", __name__):
        from .browser_cdp_tool import browser_cdp  # noqa: F401

        print("Registered: browser_cdp")
except ImportError:
    pass

try:
    import importlib.util

    if importlib.util.find_spec(".code_execution_tool", __name__):
        from .code_execution_tool import execute_code  # noqa: F401

        print("Registered: execute_code")
except ImportError:
    pass

try:
    import importlib.util

    if importlib.util.find_spec(".terminal_tool", __name__):
        from .terminal_tool import run_terminal  # noqa: F401

        print("Registered: run_terminal")
except ImportError:
    pass

try:
    import importlib.util

    if importlib.util.find_spec(".voice_tool", __name__):
        from .voice_tool import voice_stt, voice_tts  # noqa: F401

        print("Registered: voice_tts, voice_stt")
except ImportError:
    pass

try:
    import importlib.util

    if importlib.util.find_spec(".process_tool", __name__):
        from .process_tool import process_list, process_start, process_stop  # noqa: F401

        print("Registered: process_start, process_stop, process_list")
except ImportError:
    pass

__all__ = [
    "registry",
    "ToolDef",
    "delegate_task_tool",
    "subagent_status_tool",
    "subagent_steer_tool",
    "subagent_stop_tool",
    "patch_tool",
    "read_file_tool",
    "search_files_tool",
    "write_file_tool",
    "plan_create_tool",
    "plan_review_tool",
    "task_decompose_tool",
    "arxiv_search_tool",
    "paper_analyze_tool",
    "source_validator_tool",
    "compare_sources_tool",
    "extract_claims_tool",
    "synthesize_results_tool",
    "web_extract_tool",
    "web_search_tool",
]
