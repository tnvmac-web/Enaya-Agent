"""
Enaya Agent - Plan Validator
Feasibility and completeness checks for plans.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of plan validation."""
    passed: bool
    issues: list[str]
    warnings: list[str]
    score: int  # 0-100


class PlanValidator:
    """
    Validates plans for completeness, feasibility, and risks.
    """

    def __init__(self, agent):
        self.agent = agent

    def validate(self, plan: dict, criteria: list[str] = None) -> ValidationResult:
        """Validate a plan against criteria."""
        default_criteria = [
            "completeness",
            "feasibility",
            "dependency_correctness",
            "resource_estimation",
            "risk_identification",
            "testability",
            "milestone_clarity",
        ]
        criteria = criteria or default_criteria

        issues = []
        warnings = []

        # Check each criterion
        for criterion in criteria:
            if criterion == "completeness":
                issues.extend(self._check_completeness(plan))
            elif criterion == "feasibility":
                warnings.extend(self._check_feasibility(plan))
            elif criterion == "dependency_correctness":
                issues.extend(self._check_dependencies(plan))
            elif criterion == "resource_estimation":
                warnings.extend(self._check_resources(plan))
            elif criterion == "risk_identification":
                warnings.extend(self._check_risks(plan))
            elif criterion == "testability":
                warnings.extend(self._check_testability(plan))
            elif criterion == "milestone_clarity":
                warnings.extend(self._check_milestones(plan))

        score = max(0, 100 - len(issues) * 20 - len(warnings) * 5)
        passed = len(issues) == 0

        return ValidationResult(
            passed=passed,
            issues=issues,
            warnings=warnings,
            score=score,
        )

    def _check_completeness(self, plan: dict) -> list[str]:
        issues = []
        if not plan.get("phases"):
            issues.append("No phases defined")
        if not plan.get("goal"):
            issues.append("No goal specified")
        for i, phase in enumerate(plan.get("phases", [])):
            if not phase.get("tasks"):
                issues.append(f"Phase {i+1} has no tasks")
        return issues

    def _check_feasibility(self, plan: dict) -> list[str]:
        warnings = []
        total_tasks = sum(len(p.get("tasks", [])) for p in plan.get("phases", []))
        if total_tasks > 20:
            warnings.append(f"High task count ({total_tasks}) - consider grouping")
        return warnings

    def _check_dependencies(self, plan: dict) -> list[str]:
        issues = []
        task_ids = set()
        for phase in plan.get("phases", []):
            for task in phase.get("tasks", []):
                tid = task.get("task_id")
                if tid in task_ids:
                    issues.append(f"Duplicate task ID: {tid}")
                task_ids.add(tid)
                for dep in task.get("dependencies", []):
                    if dep not in task_ids and dep not in [t.get("task_id") for p in plan.get("phases", []) for t in p.get("tasks", [])]:
                        issues.append(f"Task {tid} depends on unknown task: {dep}")
        return issues

    def _check_resources(self, plan: dict) -> list[str]:
        warnings = []
        if not plan.get("metadata", {}).get("resource_estimate"):
            warnings.append("No resource estimation provided")
        return warnings

    def _check_risks(self, plan: dict) -> list[str]:
        warnings = []
        if not plan.get("metadata", {}).get("risks"):
            warnings.append("No risks identified")
        return warnings

    def _check_testability(self, plan: dict) -> list[str]:
        warnings = []
        if not plan.get("metadata", {}).get("test_criteria"):
            warnings.append("No test criteria defined")
        return warnings

    def _check_milestones(self, plan: dict) -> list[str]:
        warnings = []
        if not plan.get("metadata", {}).get("milestones"):
            warnings.append("No milestones defined")
        return warnings
