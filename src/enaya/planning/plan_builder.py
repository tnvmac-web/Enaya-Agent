"""
Enaya Agent - Plan Builder
Structured plan creation with milestones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PlanPhase:
    """A phase in an execution plan."""
    phase: int
    title: str
    tasks: list[dict]
    can_parallel: bool = False
    estimated_duration: str = "unknown"


@dataclass
class ExecutionPlan:
    """A complete execution plan."""
    goal: str
    phases: list[PlanPhase] = field(default_factory=list)
    total_tasks: int = 0
    estimated_duration: str = "unknown"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


class PlanBuilder:
    """
    Builds structured execution plans from decomposed tasks.
    """

    def __init__(self, agent):
        self.agent = agent

    def build(self, subtasks: list[dict], parallel_groups: bool = True) -> ExecutionPlan:
        """Build an execution plan from subtasks."""
        prompt = f"""Create a structured execution plan from these subtasks:

Subtasks: {subtasks}
Parallel Groups: {parallel_groups}

Return a plan with phases, each containing tasks that can run in parallel.
Include dependencies, effort estimates, and milestones."""

        result = self.agent.run_conversation(prompt)
        
        # Parse into ExecutionPlan
        return ExecutionPlan(
            goal="",
            phases=[],
        )

    def add_milestones(self, plan: ExecutionPlan, milestones: list[dict]) -> ExecutionPlan:
        """Add milestones to a plan."""
        plan.metadata["milestones"] = milestones
        return plan

    def estimate_resources(self, plan: ExecutionPlan) -> dict:
        """Estimate resource requirements for a plan."""
        return {
            "total_subagents": sum(1 for p in plan.phases for t in p.tasks if t.get("can_parallel")),
            "sequential_tasks": sum(1 for p in plan.phases for t in p.tasks if not t.get("can_parallel")),
            "estimated_token_budget": 100000,
        }