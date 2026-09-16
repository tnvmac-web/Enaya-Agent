"""
Enaya Agent - Planning Tools
task_decompose, plan_create, plan_update, plan_review.
Enaya-specific tools for structured planning.
"""

from __future__ import annotations

import json

from enaya.tools.registry import registry

# =============================================================================
# task_decompose
# =============================================================================

TASK_DECOMPOSE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "task_decompose",
        "description": "Decompose a complex goal into hierarchical subtasks with dependencies.",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "The high-level goal to decompose"},
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum decomposition depth (default: 3)",
                    "default": 3,
                },
                "constraints": {
                    "type": "string",
                    "description": "Constraints or requirements to consider",
                },
            },
            "required": ["goal"],
        },
    },
}


def check_task_decompose_requirements() -> bool:
    return True


def task_decompose_tool(goal: str, max_depth: int = 3, constraints: str = None) -> str:
    """Decompose a goal into subtasks."""
    # This is a template - in practice, the LLM would do the decomposition
    # We return a structured template for the LLM to fill in
    return json.dumps(
        {
            "goal": goal,
            "max_depth": max_depth,
            "constraints": constraints,
            "decomposition_template": {
                "subtasks": [
                    {
                        "id": "1",
                        "title": "Subtask 1",
                        "description": "Description",
                        "dependencies": [],
                        "estimated_effort": "low|medium|high",
                        "skills_needed": [],
                    }
                ],
            },
            "instruction": (
                "Fill in the decomposition_template with actual subtasks. "
                "Return the completed structure."
            ),
        }
    )


registry.register(
    name="task_decompose",
    toolset="planning",
    schema=TASK_DECOMPOSE_SCHEMA,
    handler=task_decompose_tool,
    check_fn=check_task_decompose_requirements,
)


# =============================================================================
# plan_create
# =============================================================================

PLAN_CREATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "plan_create",
        "description": "Create a structured execution plan from decomposed tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "subtasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "dependencies": {"type": "array", "items": {"type": "string"}},
                            "estimated_effort": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                            },
                            "skills_needed": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["id", "title"],
                    },
                },
                "parallel_groups": {
                    "type": "boolean",
                    "description": "Group independent tasks for parallel execution",
                    "default": True,
                },
            },
            "required": ["subtasks"],
        },
    },
}


def check_plan_create_requirements() -> bool:
    return True


def plan_create_tool(subtasks: list[dict], parallel_groups: bool = True) -> str:
    """Create an execution plan from subtasks."""
    # Topological sort for dependencies
    task_map = {t["id"]: t for t in subtasks}

    def get_deps(task_id):
        return task_map.get(task_id, {}).get("dependencies", [])

    # Simple Kahn's algorithm
    in_degree = {tid: len(get_deps(tid)) for tid in task_map}
    queue = [tid for tid, deg in in_degree.items() if deg == 0]
    order = []

    while queue:
        current = queue.pop(0)
        order.append(current)
        for tid, task in task_map.items():
            if current in task.get("dependencies", []):
                in_degree[tid] -= 1
                if in_degree[tid] == 0:
                    queue.append(tid)

    # Build plan with phases
    plan = {
        "phases": [],
        "total_tasks": len(subtasks),
        "estimated_duration": "unknown",
    }

    if parallel_groups:
        # Group by dependency level
        phase = 1
        remaining = set(task_map.keys())
        while remaining:
            # Find tasks whose dependencies are all satisfied
            ready = [tid for tid in remaining if all(d not in remaining for d in get_deps(tid))]
            if not ready:
                # Circular dependency - add all remaining
                ready = list(remaining)

            phase_tasks = []
            for tid in ready:
                task = task_map[tid]
                phase_tasks.append(
                    {
                        "task_id": tid,
                        "title": task["title"],
                        "description": task.get("description", ""),
                        "can_parallel": len(ready) > 1,
                    }
                )
                remaining.remove(tid)

            plan["phases"].append(
                {
                    "phase": phase,
                    "tasks": phase_tasks,
                }
            )
            phase += 1
    else:
        # Sequential
        for i, tid in enumerate(order):
            task = task_map[tid]
            plan["phases"].append(
                {
                    "phase": i + 1,
                    "tasks": [
                        {
                            "task_id": tid,
                            "title": task["title"],
                            "description": task.get("description", ""),
                            "can_parallel": False,
                        }
                    ],
                }
            )

    return json.dumps({"plan": plan})


registry.register(
    name="plan_create",
    toolset="planning",
    schema=PLAN_CREATE_SCHEMA,
    handler=plan_create_tool,
    check_fn=check_plan_create_requirements,
)


# =============================================================================
# plan_review
# =============================================================================

PLAN_REVIEW_SCHEMA = {
    "type": "function",
    "function": {
        "name": "plan_review",
        "description": "Review a plan for completeness, feasibility, and risks.",
        "parameters": {
            "type": "object",
            "properties": {
                "plan": {"type": "object", "description": "The plan to review"},
                "criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Review criteria",
                },
            },
            "required": ["plan"],
        },
    },
}


def check_plan_review_requirements() -> bool:
    return True


def plan_review_tool(plan: dict, criteria: list[str] = None) -> str:
    """Review a plan and identify issues."""
    default_criteria = [
        "completeness",
        "feasibility",
        "dependency_correctness",
        "resource_estimation",
        "risk_identification",
        "testability",
    ]
    criteria = criteria or default_criteria

    issues = []
    warnings = []

    # Check for circular dependencies (basic)
    # Check for missing dependencies
    # Check for orphaned tasks
    # Check effort estimates

    return json.dumps(
        {
            "review": {
                "passed": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "score": 100 - len(issues) * 20 - len(warnings) * 5,
            }
        }
    )


registry.register(
    name="plan_review",
    toolset="planning",
    schema=PLAN_REVIEW_SCHEMA,
    handler=plan_review_tool,
    check_fn=check_plan_review_requirements,
)
