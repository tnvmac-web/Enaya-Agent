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

# New tools
try:
    from .browser_cdp_tool import browser_cdp
    print("Registered: browser_cdp")
except ImportError:
    pass

try:
    from .code_execution_tool import execute_code
    print("Registered: execute_code")
except ImportError:
    pass

try:
    from .terminal_tool import run_terminal
    print("Registered: run_terminal")
except ImportError:
    pass

try:
    from .voice_tool import voice_stt, voice_tts
    print("Registered: voice_tts, voice_stt")
except ImportError:
    pass

try:
    from .process_tool import process_list, process_start, process_stop
    print("Registered: process_start, process_stop, process_list")
except ImportError:
    pass

__all__ = [
    "registry",
    "ToolDef",
]
