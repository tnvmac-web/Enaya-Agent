"""
Enaya Agent - Delegation Policies
When and how to delegate tasks to subagents.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DelegationTrigger(Enum):
    """Conditions that trigger delegation."""
    COMPLEXITY_THRESHOLD = "complexity_threshold"
    DOMAIN_SPECIALIZATION = "domain_specialization"
    PARALLELIZABLE = "parallelizable"
    LONG_RUNNING = "long_running"
    USER_REQUEST = "user_request"


@dataclass
class DelegationPolicy:
    """Policy for when to delegate."""
    # Complexity thresholds
    max_single_agent_complexity: int = 7  # 1-10 scale
    max_estimated_tokens: int = 50000
    max_estimated_time_seconds: int = 120

    # Domain routing
    research_domains: list[str] = None
    code_domains: list[str] = None
    planning_domains: list[str] = None

    # Parallelization
    min_parallel_tasks: int = 2
    max_parallel_subagents: int = 3

    # Resource limits
    max_subagent_budget: int = 100000  # tokens
    max_total_delegation_budget: int = 500000

    # Fallback
    allow_recursive_delegation: bool = False
    max_delegation_depth: int = 2

    def __post_init__(self):
        if self.research_domains is None:
            self.research_domains = ["research", "analysis", "literature review", "market research", "academic"]
        if self.code_domains is None:
            self.code_domains = ["coding", "debugging", "refactoring", "code review", "architecture"]
        if self.planning_domains is None:
            self.planning_domains = ["planning", "strategy", "roadmap", "decomposition", "scheduling"]


DEFAULT_DELEGATION_POLICY = DelegationPolicy()


def should_delegate(
    task: str,
    context: str,
    policy: DelegationPolicy = None,
    current_depth: int = 0,
) -> tuple[bool, str, dict]:
    """
    Determine if a task should be delegated.
    Returns (should_delegate, reason, suggested_config).
    """
    policy = policy or DEFAULT_DELEGATION_POLICY

    # Check depth limit
    if current_depth >= policy.max_delegation_depth:
        return False, "max_delegation_depth_reached", {}

    # Check for explicit user request
    if "[DELEGATE]" in task.upper() or "delegate" in task.lower():
        return True, "user_requested", {}

    # Estimate complexity (simplified heuristic)
    complexity = _estimate_complexity(task, context)
    if complexity > policy.max_single_agent_complexity:
        return True, f"complexity_threshold_exceeded ({complexity} > {policy.max_single_agent_complexity})", {
            "suggested_max_iterations": 50,
            "suggested_toolsets": _suggest_toolsets(task),
        }

    # Check for parallelizable subtasks
    parallel_tasks = _count_parallelizable_subtasks(task)
    if parallel_tasks >= policy.min_parallel_tasks:
        return True, f"parallelizable_subtasks ({parallel_tasks} >= {policy.min_parallel_tasks})", {
            "suggested_max_iterations": 30,
            "suggested_toolsets": ["core", "research"],
        }

    # Check domain specialization
    domain = _detect_domain(task)
    if domain in policy.research_domains:
        return True, f"research_domain ({domain})", {
            "suggested_toolsets": ["core", "research", "synthesis"],
        }
    if domain in policy.code_domains:
        return True, f"code_domain ({domain})", {
            "suggested_toolsets": ["core", "planning", "delegation"],
        }
    if domain in policy.planning_domains:
        return True, f"planning_domain ({domain})", {
            "suggested_toolsets": ["core", "planning"],
        }

    return False, "no_delegation_needed", {}


def _estimate_complexity(task: str, context: str) -> int:
    """Estimate task complexity 1-10."""
    score = 1
    text = (task + " " + context).lower()

    # Length factor
    score += min(len(text) // 1000, 3)

    # Keywords indicating complexity
    complex_keywords = [
        "multiple", "various", "several", "compare", "analyze", "research",
        "investigate", "comprehensive", "thorough", "deep", "full",
        "architecture", "system", "design", "implement", "build",
        "integrate", "migrate", "refactor", "optimize",
    ]
    for kw in complex_keywords:
        if kw in text:
            score += 1

    return min(score, 10)


def _count_parallelizable_subtasks(task: str) -> int:
    """Count potentially parallelizable subtasks."""
    # Simplified - look for list-like language
    count = 1
    text = task.lower()
    for kw in ["and", "also", "additionally", "furthermore", "plus", "each", "every"]:
        count += text.count(kw)
    return min(count, 5)


def _detect_domain(task: str) -> str:
    """Detect task domain."""
    text = task.lower()
    if any(kw in text for kw in ["research", "paper", "academic", "literature", "study", "analyze"]):
        return "research"
    if any(kw in text for kw in ["code", "implement", "debug", "refactor", "function", "class", "api"]):
        return "coding"
    if any(kw in text for kw in ["plan", "strategy", "roadmap", "decompose", "schedule", "milestone"]):
        return "planning"
    return "general"


def _suggest_toolsets(task: str) -> list[str]:
    """Suggest toolsets based on task."""
    text = task.lower()
    toolsets = ["core"]

    if any(kw in text for kw in ["research", "search", "paper", "academic", "web"]):
        toolsets.append("research")
    if any(kw in text for kw in ["plan", "decompose", "strategy", "roadmap"]):
        toolsets.append("planning")
    if any(kw in text for kw in ["delegate", "subagent", "parallel", "multiple"]):
        toolsets.append("delegation")
    if any(kw in text for kw in ["synthesize", "compare", "aggregate", "merge"]):
        toolsets.append("synthesis")

    return toolsets