#!/usr/bin/env python3
"""
Enaya Agent - Kanban System
SQLite-backed task board for multi-agent coordination.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# =============================================================================
# Kanban Data Classes
# =============================================================================

class TaskStatus(Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class KanbanTask:
    """Kanban task/card."""
    id: str
    board_id: str
    column_id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee: str | None = None  # agent name or user
    labels: list[str] = field(default_factory=list)
    due_date: float | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class KanbanColumn:
    """Kanban board column."""
    id: str
    board_id: str
    name: str
    status: TaskStatus
    order: int
    wip_limit: int | None = None
    color: str = "#58a6ff"


@dataclass
class KanbanBoard:
    """Kanban board."""
    id: str
    name: str
    description: str = ""
    owner: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    columns: list[KanbanColumn] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# =============================================================================
# Kanban Store
# =============================================================================

class KanbanStore:
    """SQLite-backed Kanban storage."""

    def __init__(self, profile: str = "default"):
        self.profile = profile
        self.db_path = self._get_db_path()
        self._init_db()

    def _get_db_path(self) -> Path:
        enaya_home = Path(os.environ.get("ENAYA_HOME", Path.home() / ".enaya"))
        if self.profile != "default":
            enaya_home = enaya_home / "profiles" / self.profile
        enaya_home.mkdir(parents=True, exist_ok=True)
        return enaya_home / "kanban.db"

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            # Boards
            conn.execute("""
                CREATE TABLE IF NOT EXISTS boards (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    metadata TEXT
                )
            """)

            # Columns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS columns (
                    id TEXT PRIMARY KEY,
                    board_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    order_num INTEGER NOT NULL,
                    wip_limit INTEGER,
                    color TEXT,
                    FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
                )
            """)

            # Tasks
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    board_id TEXT NOT NULL,
                    column_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    priority INTEGER DEFAULT 2,
                    assignee TEXT,
                    labels TEXT,
                    due_date REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    metadata TEXT,
                    FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
                    FOREIGN KEY (column_id) REFERENCES columns(id) ON DELETE CASCADE
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_board ON tasks(board_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_column ON tasks(column_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # =============================================================================
    # Board Operations
    # =============================================================================

    def create_board(self, name: str, description: str = "", owner: str = "") -> KanbanBoard:
        board_id = str(uuid.uuid4())[:12]
        now = time.time()

        board = KanbanBoard(
            id=board_id,
            name=name,
            description=description,
            owner=owner,
            created_at=now,
            updated_at=now,
        )

        # Add default columns
        default_columns = [
            ("backlog", "Backlog", TaskStatus.BACKLOG, 0),
            ("todo", "To Do", TaskStatus.TODO, 1),
            ("in_progress", "In Progress", TaskStatus.IN_PROGRESS, 2),
            ("review", "Review", TaskStatus.REVIEW, 3),
            ("done", "Done", TaskStatus.DONE, 4),
        ]

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO boards (id, name, description, owner, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (board_id, name, description, owner, now, now, "{}"))

            for i, (col_id, name, status, order) in enumerate(default_columns):
                col_uuid = str(uuid.uuid4())[:12]
                conn.execute("""
                    INSERT INTO columns (id, board_id, name, status, order_num, color)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (col_uuid, board_id, name, status.value, order, "#58a6ff"))

        return self.get_board(board_id)

    def get_board(self, board_id: str) -> KanbanBoard | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM boards WHERE id = ?", (board_id,)).fetchone()
            if not row:
                return None

            board = KanbanBoard(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                owner=row["owner"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )

            # Load columns
            cols = conn.execute("SELECT * FROM columns WHERE board_id = ? ORDER BY order_num", (board_id,)).fetchall()
            board.columns = [
                KanbanColumn(
                    id=c["id"],
                    board_id=c["board_id"],
                    name=c["name"],
                    status=TaskStatus(c["status"]),
                    order=c["order_num"],
                    wip_limit=c["wip_limit"],
                    color=c["color"] or "#58a6ff",
                )
                for c in cols
            ]

            return board

    def list_boards(self) -> list[KanbanBoard]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM boards ORDER BY updated_at DESC").fetchall()
            return [self.get_board(r["id"]) for r in rows]

    def delete_board(self, board_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM boards WHERE id = ?", (board_id,))
            return cursor.rowcount > 0

    # =============================================================================
    # Column Operations
    # =============================================================================

    def add_column(self, board_id: str, name: str, status: TaskStatus, color: str = "#58a6ff") -> KanbanColumn:
        column_id = str(uuid.uuid4())[:12]

        with self._get_connection() as conn:
            # Get max order
            max_order = conn.execute("SELECT MAX(order_num) FROM columns WHERE board_id = ?", (board_id,)).fetchone()
            order = (max_order[0] or -1) + 1

            conn.execute("""
                INSERT INTO columns (id, board_id, name, status, order_num, color)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (column_id, board_id, name, status.value, order, color))

        return KanbanColumn(
            id=column_id,
            board_id=board_id,
            name=name,
            status=status,
            order=order,
            color=color,
        )

    def update_column(self, column_id: str, **kwargs) -> bool:
        with self._get_connection() as conn:
            updates = []
            params = []
            for key, value in kwargs.items():
                if key == "wip_limit":
                    updates.append("wip_limit = ?")
                elif key == "color":
                    updates.append("color = ?")
                elif key == "name":
                    updates.append("name = ?")
                elif key == "status":
                    updates.append("status = ?")
                    value = value.value if isinstance(value, TaskStatus) else value
                elif key == "order":
                    updates.append("order_num = ?")
                else:
                    continue
                params.append(value)

            if not updates:
                return False

            params.append(column_id)
            cursor = conn.execute(f"UPDATE columns SET {', '.join(updates)} WHERE id = ?", params)
            return cursor.rowcount > 0

    def delete_column(self, column_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM columns WHERE id = ?", (column_id,))
            return cursor.rowcount > 0

    def reorder_columns(self, board_id: str, column_order: list[str]) -> bool:
        """Reorder columns by providing list of column IDs in new order."""
        with self._get_connection() as conn:
            for i, col_id in enumerate(column_order):
                conn.execute("UPDATE columns SET order_num = ? WHERE id = ? AND board_id = ?", (i, col_id, board_id))
            return True

    # =============================================================================
    # Task Operations
    # =============================================================================

    def create_task(
        self,
        board_id: str,
        column_id: str,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        assignee: str = None,
        labels: list[str] = None,
        due_date: float = None,
    ) -> KanbanTask:
        task_id = str(uuid.uuid4())[:12]
        now = time.time()

        task = KanbanTask(
            id=task_id,
            board_id=board_id,
            column_id=column_id,
            title=title,
            description=description,
            status=TaskStatus.BACKLOG,
            priority=priority,
            assignee=assignee,
            labels=labels or [],
            due_date=due_date,
            created_at=now,
            updated_at=now,
        )

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO tasks (id, board_id, column_id, title, description, status, priority, assignee, labels, due_date, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id, board_id, column_id, title, description,
                TaskStatus.BACKLOG.value, priority.value, assignee,
                json.dumps(labels or []), due_date, now, now, "{}"
            ))

        return task

    def get_task(self, task_id: str) -> KanbanTask | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def get_tasks(self, board_id: str = None, column_id: str = None, assignee: str = None) -> list[KanbanTask]:
        with self._get_connection() as conn:
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []

            if board_id:
                query += " AND board_id = ?"
                params.append(board_id)
            if column_id:
                query += " AND column_id = ?"
                params.append(column_id)
            if assignee:
                query += " AND assignee = ?"
                params.append(assignee)

            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_task(r) for r in rows]

    def _row_to_task(self, row: sqlite3.Row) -> KanbanTask:
        return KanbanTask(
            id=row["id"],
            board_id=row["board_id"],
            column_id=row["column_id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            priority=TaskPriority(row["priority"]),
            assignee=row["assignee"],
            labels=json.loads(row["labels"]) if row["labels"] else [],
            due_date=row["due_date"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def move_task(self, task_id: str, column_id: str) -> bool:
        """Move task to a different column."""
        with self._get_connection() as conn:
            # Get task to check current column
            task = self.get_task(task_id)
            if not task:
                return False

            old_column = task.column_id
            new_status = self._get_column_status(column_id)

            now = time.time()
            updates = ["column_id = ?", "status = ?", "updated_at = ?"]
            params = [column_id, new_status.value if new_status else TaskStatus.TODO.value, time.time()]

            if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
                updates.append("started_at = ?")
                params.append(time.time())
            elif new_status == TaskStatus.DONE and not task.completed_at:
                updates.append("completed_at = ?")
                params.append(time.time())

            params.append(task_id)

            cursor = conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
            return cursor.rowcount > 0

    def _get_column_status(self, column_id: str) -> TaskStatus | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT status FROM columns WHERE id = ?", (column_id,)).fetchone()
            if row:
                return TaskStatus(row["status"])
        return None

    def update_task(self, task_id: str, **kwargs) -> bool:
        with self._get_connection() as conn:
            updates = []
            params = []

            for key, value in kwargs.items():
                if key == "title":
                    updates.append("title = ?")
                elif key == "description":
                    updates.append("description = ?")
                elif key == "priority":
                    updates.append("priority = ?")
                    value = value.value if isinstance(value, TaskPriority) else value
                elif key == "assignee":
                    updates.append("assignee = ?")
                elif key == "labels":
                    updates.append("labels = ?")
                    value = json.dumps(value)
                elif key == "due_date":
                    updates.append("due_date = ?")
                elif key == "metadata":
                    updates.append("metadata = ?")
                    value = json.dumps(value)
                else:
                    continue
                params.append(value)

            if not updates:
                return False

            updates.append("updated_at = ?")
            params.append(time.time())
            params.append(task_id)

            cursor = conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
            return cursor.rowcount > 0

    def delete_task(self, task_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

    def assign_task(self, task_id: str, assignee: str) -> bool:
        """Assign task to an agent/user."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET assignee = ?, updated_at = ? WHERE id = ?",
                (assignee, time.time(), task_id)
            )
            return cursor.rowcount > 0

    def add_label(self, task_id: str, label: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        if label not in task.labels:
            task.labels.append(label)
            return self.update_task(task_id, labels=task.labels)
        return True

    def remove_label(self, task_id: str, label: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        if label in task.labels:
            task.labels.remove(label)
            return self.update_task(task_id, labels=task.labels)
        return True

    # =============================================================================
    # Board View
    # =============================================================================

    def get_board_view(self, board_id: str) -> dict:
        """Get complete board view with columns and tasks."""
        board = self.get_board(board_id)
        if not board:
            return {}

        with self._get_connection() as conn:
            columns = conn.execute("SELECT * FROM columns WHERE board_id = ? ORDER BY order_num", (board_id,)).fetchall()
            tasks = conn.execute("SELECT * FROM tasks WHERE board_id = ?", (board_id,)).fetchall()

        # Group tasks by column
        tasks_by_column = {}
        for task_row in tasks:
            task = self._row_to_task(task_row)
            if task.column_id not in tasks_by_column:
                tasks_by_column[task.column_id] = []
            tasks_by_column[task.column_id].append(task)

        return {
            "board": {
                "id": board.id,
                "name": board.name,
                "description": board.description,
            },
            "columns": [
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status.value,
                    "order": c.order,
                    "wip_limit": c.wip_limit,
                    "color": c.color,
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "description": t.description,
                            "priority": t.priority.name,
                            "assignee": t.assignee,
                            "created_at": t.created_at,
                        }
                        for t in tasks_by_column.get(c.id, [])
                    ],
                }
                for c in board.columns
            ],
        }


# =============================================================================
# Kanban Manager (High-level API)
# =============================================================================

class KanbanManager:
    """High-level Kanban manager with agent integration."""

    def __init__(self, profile: str = "default"):
        self.profile = profile
        self.store = KanbanStore(profile)

    def create_board(self, name: str, description: str = "") -> KanbanBoard:
        return self.store.create_board(name, description, self.profile)

    def get_board(self, board_id: str) -> KanbanBoard | None:
        return self.store.get_board(board_id)

    def list_boards(self) -> list[KanbanBoard]:
        return self.store.list_boards()

    def create_task(
        self,
        board_id: str,
        column_id: str,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        assignee: str = None,
    ) -> KanbanTask:
        return self.store.create_task(board_id, column_id, title, description, priority, assignee)

    def move_task(self, task_id: str, column_id: str) -> bool:
        return self.store.move_task(task_id, column_id)

    def assign_task(self, task_id: str, assignee: str) -> bool:
        return self.store.assign_task(task_id, assignee)

    def get_board_view(self, board_id: str) -> dict:
        return self.store.get_board_view(board_id)

    def get_task(self, task_id: str) -> KanbanTask | None:
        return self.store.get_task(task_id)

    def update_task(self, task_id: str, **kwargs) -> bool:
        return self.store.update_task(task_id, **kwargs)

    def delete_task(self, task_id: str) -> bool:
        return self.store.delete_task(task_id)

    def add_label(self, task_id: str, label: str) -> bool:
        return self.store.add_label(task_id, label)

    def remove_label(self, task_id: str, label: str) -> bool:
        return self.store.remove_label(task_id, label)


# =============================================================================
# Agent Integration
# =============================================================================

class KanbanAgent:
    """Agent that can interact with Kanban boards."""

    def __init__(self, manager: KanbanManager):
        self.manager = manager

    def create_task_from_prompt(self, board_id: str, prompt: str) -> KanbanTask:
        """Create a task from a natural language prompt."""
        # Parse prompt for title, description, priority
        # This is a simplified version - real implementation would use LLM
        lines = prompt.strip().split("\n")
        title = lines[0] if lines else "Untitled Task"
        description = "\n".join(lines[1:]) if len(lines) > 1 else ""

        # Default to first column (backlog)
        board = self.manager.store.get_board(board_id)
        if not board or not board.columns:
            raise ValueError("Board not found or has no columns")

        return self.manager.create_task(
            board_id=board_id,
            column_id=board.columns[0].id,
            title=title,
            description=description,
        )

    def move_task_to_status(self, task_id: str, status: TaskStatus) -> bool:
        """Move task to column matching status."""
        task = self.manager.store.get_task(task_id)
        if not task:
            return False

        board = self.manager.store.get_board(task.board_id)
        if not board:
            return False

        # Find column with matching status
        target_column = next((c for c in board.columns if c.status == status), None)
        if not target_column:
            return False

        return self.manager.move_task(task_id, target_column.id)

    def get_agent_tasks(self, agent_name: str) -> list[KanbanTask]:
        """Get all tasks assigned to an agent."""
        # Search across all boards
        all_tasks = []
        for board in self.manager.store.list_boards():
            tasks = self.manager.store.get_tasks(board_id=board.id, assignee=agent_name)
            all_tasks.extend(tasks)
        return all_tasks


# =============================================================================
# CLI Commands
# =============================================================================

def kanban_create_board(name: str, description: str = "") -> str:
    manager = KanbanManager()
    board = manager.create_board(name, description)
    print(f"Created board: {board.id} ({board.name})")
    return board.id


def kanban_list_boards() -> list[dict]:
    manager = KanbanManager()
    return [
        {"id": b.id, "name": b.name, "description": b.description, "columns": len(b.columns)}
        for b in manager.list_boards()
    ]


def kanban_add_task(board_id: str, column: str, title: str, description: str = "", priority: str = "medium", assignee: str = None) -> str:
    manager = KanbanManager()
    board = manager.store.get_board(board_id)
    if not board:
        print(f"Board not found: {board_id}")
        return ""

    # Find column by name or status
    target_column = next((c for c in board.columns if c.name.lower() == column.lower() or c.status.value == column.lower()), None)
    if not target_column:
        target_column = board.columns[0]  # Default to first column

    priority = TaskPriority[priority.upper()]
    task = manager.create_task(board_id, target_column.id, title, description, priority, assignee)
    print(f"Created task: {task.id} ({task.title}) in {target_column.name}")
    return task.id


def kanban_move_task(task_id: str, column: str) -> bool:
    manager = KanbanManager()
    # Find board containing task
    task = manager.store.get_task(task_id)
    if not task:
        print(f"Task not found: {task_id}")
        return False

    board = manager.store.get_board(task.board_id)
    if not board:
        return False

    target_column = next((c for c in board.columns if c.name.lower() == column.lower() or c.status.value == column.lower()), None)
    if not target_column:
        print(f"Column not found: {column}")
        return False

    if manager.move_task(task_id, target_column.id):
        print(f"Moved task {task_id} to {target_column.name}")
        return True
    return False


def kanban_board_view(board_id: str) -> dict:
    manager = KanbanManager()
    return manager.get_board_view(board_id)
