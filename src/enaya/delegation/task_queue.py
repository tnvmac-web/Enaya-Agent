"""
Enaya Agent - Task Queue
Priority-based task distribution for delegation.
"""

from __future__ import annotations

import heapq
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskPriority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class QueuedTask:
    """A task in the delegation queue."""

    id: str
    task: str
    context: str
    priority: TaskPriority = TaskPriority.NORMAL
    model: str | None = None
    max_iterations: int = 50
    toolsets: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # Task IDs that must complete first
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: datetime | None = None

    def __lt__(self, other: QueuedTask) -> bool:
        """For heap ordering: lower priority value = higher priority."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class TaskQueue:
    """
    Priority-based task queue with dependency resolution.
    """

    def __init__(self):
        self._queue: list[QueuedTask] = []
        self._completed: set[str] = set()
        self._running: set[str] = set()
        self._failed: set[str] = set()

    def enqueue(
        self,
        task: str,
        context: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        model: str = None,
        max_iterations: int = 50,
        toolsets: list[str] = None,
        dependencies: list[str] = None,
        **metadata,
    ) -> str:
        """Add a task to the queue."""
        task_id = str(uuid.uuid4())[:12]
        queued = QueuedTask(
            id=task_id,
            task=task,
            context=context,
            priority=priority,
            model=model,
            max_iterations=max_iterations,
            toolsets=toolsets or [],
            dependencies=dependencies or [],
            metadata=metadata,
        )
        heapq.heappush(self._queue, queued)
        return task_id

    def dequeue_ready(self) -> QueuedTask | None:
        """Get next task whose dependencies are satisfied."""
        # Find first task with satisfied dependencies
        for i, task in enumerate(self._queue):
            if all(dep in self._completed for dep in task.dependencies):
                self._queue.pop(i)
                heapq.heapify(self._queue)  # Restore heap property
                self._running.add(task.id)
                return task
        return None

    def mark_completed(self, task_id: str) -> None:
        """Mark task as completed."""
        self._completed.add(task_id)
        self._running.discard(task_id)

    def mark_failed(self, task_id: str) -> None:
        """Mark task as failed."""
        self._failed.add(task_id)
        self._running.discard(task_id)

    def get_pending(self) -> list[QueuedTask]:
        """Get all pending tasks."""
        return list(self._queue)

    def get_running(self) -> set[str]:
        return self._running.copy()

    def get_completed(self) -> set[str]:
        return self._completed.copy()

    def get_failed(self) -> set[str]:
        return self._failed.copy()

    def stats(self) -> dict:
        return {
            "queued": len(self._queue),
            "running": len(self._running),
            "completed": len(self._completed),
            "failed": len(self._failed),
        }
