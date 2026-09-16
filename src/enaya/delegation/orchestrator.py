"""
Enaya Agent - Delegation Orchestrator
Subagent lifecycle management, task distribution, result aggregation.
Core component for multi-agent orchestration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from enaya.run_agent import AgentConfig, AIAgent


class SubagentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class SubagentTask:
    """A task delegated to a subagent."""
    id: str
    task: str
    context: str
    model: str
    max_iterations: int
    toolsets: list[str]
    status: SubagentStatus = SubagentStatus.PENDING
    result: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    steer_messages: list[str] = field(default_factory=list)
    agent: AIAgent | None = None


class DelegationOrchestrator:
    """
    Manages subagent lifecycle: spawn, monitor, collect results, synthesize.
    """

    def __init__(self, parent_agent: AIAgent):
        self.parent_agent = parent_agent
        self.subagents: dict[str, SubagentTask] = {}
        self.task_queue: list[str] = []
        self.max_parallel = 3
        self._running_count = 0

    def delegate(
        self,
        task: str,
        context: str,
        model: str = None,
        max_iterations: int = 50,
        toolsets: list[str] = None,
    ) -> str:
        """
        Spawn a subagent for a task.
        Returns subagent ID.
        """
        subagent_id = str(uuid.uuid4())[:12]

        # Use parent's config as base
        parent_config = self.parent_agent.config
        subagent_config = AgentConfig(
            model=model or parent_config.model,
            provider=parent_config.provider,
            base_url=parent_config.base_url,
            api_key=parent_config.api_key,
            api_mode=parent_config.api_mode,
            max_turns=max_iterations,
            temperature=parent_config.temperature,
            top_p=parent_config.top_p,
            toolsets=toolsets or parent_config.toolsets,
            disabled_tools=parent_config.disabled_tools,
            fallback_providers=parent_config.fallback_providers,
            profile=parent_config.profile,
            platform="subagent",
            chat_type="delegation",
            chat_id=subagent_id,
        )

        # Create subagent
        subagent = AIAgent(subagent_config)

        # Create task record
        task_record = SubagentTask(
            id=subagent_id,
            task=task,
            context=context,
            model=subagent_config.model,
            max_iterations=max_iterations,
            toolsets=toolsets or parent_config.toolsets,
            agent=subagent,
        )

        self.subagents[subagent_id] = task_record
        self.task_queue.append(subagent_id)

        # Start execution if under limit
        self._try_start_next()

        return subagent_id

    def _try_start_next(self) -> None:
        """Start next queued task if under parallel limit."""
        while self._running_count < self.max_parallel and self.task_queue:
            subagent_id = self.task_queue.pop(0)
            self._run_subagent(subagent_id)

    def _run_subagent(self, subagent_id: str) -> None:
        """Execute a subagent task."""
        task = self.subagents.get(subagent_id)
        if not task or task.status != SubagentStatus.PENDING:
            return

        task.status = SubagentStatus.RUNNING
        task.started_at = datetime.now()
        self._running_count += 1

        # Build prompt with context and any steer messages
        prompt = f"""[DELEGATED SUBAGENT TASK]

Task: {task.task}

Context:
{task.context}
"""
        if task.steer_messages:
            prompt += "\nGuidance from parent:\n" + "\n".join(f"- {m}" for m in task.steer_messages)

        prompt += """

You are a subagent with isolated context. Complete this task and return your final result.
Think step by step. Use tools as needed. Provide a thorough response.
"""

        # Run in background (simplified - real impl would use threading/async)
        try:
            result = task.agent.run_conversation(prompt)
            task.result = result
            task.status = SubagentStatus.COMPLETED
        except Exception as e:
            task.error = str(e)
            task.status = SubagentStatus.FAILED
        finally:
            task.completed_at = datetime.now()
            self._running_count -= 1
            self._try_start_next()

    def get_status(self, subagent_id: str = None) -> dict:
        """Get status of subagent(s)."""
        if subagent_id:
            task = self.subagents.get(subagent_id)
            if not task:
                return {"error": f"Subagent not found: {subagent_id}"}
            return self._task_to_dict(task)
        else:
            return {
                "subagents": [self._task_to_dict(t) for t in self.subagents.values()],
                "running": self._running_count,
                "queued": len(self.task_queue),
            }

    def _task_to_dict(self, task: SubagentTask) -> dict:
        return {
            "id": task.id,
            "task": task.task,
            "status": task.status.value,
            "model": task.model,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "has_result": task.result is not None,
            "has_error": task.error is not None,
        }

    def steer(self, subagent_id: str, message: str) -> bool:
        """Send guidance to a running subagent."""
        task = self.subagents.get(subagent_id)
        if not task or task.status != SubagentStatus.RUNNING:
            return False

        task.steer_messages.append(message)
        # In real impl, this would interrupt the subagent's API call
        return True

    def stop(self, subagent_id: str) -> bool:
        """Stop a running subagent."""
        task = self.subagents.get(subagent_id)
        if not task or task.status not in (SubagentStatus.PENDING, SubagentStatus.RUNNING):
            return False

        if task.status == SubagentStatus.RUNNING:
            task.agent.interrupt()
            self._running_count -= 1
            self._try_start_next()

        task.status = SubagentStatus.STOPPED
        task.completed_at = datetime.now()
        return True

    def collect_results(self, subagent_ids: list[str] = None) -> list[dict]:
        """Collect results from completed subagents."""
        targets = subagent_ids or [tid for tid, t in self.subagents.items() if t.status == SubagentStatus.COMPLETED]
        results = []
        for tid in targets:
            task = self.subagents.get(tid)
            if task and task.result:
                results.append({
                    "subagent_id": tid,
                    "task": task.task,
                    "result": task.result,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                })
        return results

    def wait_for_all(self, timeout: float = 300.0) -> list[dict]:
        """Wait for all subagents to complete."""
        import time
        start = time.time()
        while self._running_count > 0 or self.task_queue:
            if time.time() - start > timeout:
                break
            time.sleep(0.5)
        return self.collect_results()
