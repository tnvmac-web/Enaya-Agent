"""
Enaya Agent - Task Decomposer
Hierarchical task breakdown for complex goals.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Subtask:
    """A decomposed subtask."""

    id: str
    title: str
    description: str
    dependencies: list[str]
    estimated_effort: str  # low, medium, high
    skills_needed: list[str]
    domain: str = "general"


class TaskDecomposer:
    """
    Decomposes complex goals into hierarchical subtasks.
    """

    def __init__(self, agent):
        self.agent = agent

    def decompose(self, goal: str, max_depth: int = 3, constraints: str = None) -> list[Subtask]:
        """Decompose a goal into subtasks."""
        prompt = (
            "Decompose this goal into hierarchical subtasks:\n\n"
            f"Goal: {goal}\n"
            f"Max Depth: {max_depth}\n"
            f"Constraints: {constraints or 'None'}\n\n"
            "Return a structured list of subtasks with:\n"
            "- id (unique identifier)\n"
            "- title\n"
            "- description\n"
            "- dependencies (list of subtask ids)\n"
            "- estimated_effort (low/medium/high)\n"
            "- skills_needed (list)\n"
            "- domain (research/coding/planning/general)\n\n"
            "Focus on creating independent, parallelizable subtasks where possible."
        )

        self.agent.run_conversation(prompt)

        # Parse result into Subtask objects
        # Simplified - real impl would parse structured output
        return []

    def estimate_total_effort(self, subtasks: list[Subtask]) -> dict:
        """Estimate total effort and critical path."""
        effort_map = {"low": 1, "medium": 3, "high": 5}
        total = sum(effort_map.get(s.estimated_effort, 1) for s in subtasks)

        # Find critical path (simplified)
        return {
            "total_effort_points": total,
            "estimated_hours": total * 2,
            "critical_path_length": len(subtasks),
        }
