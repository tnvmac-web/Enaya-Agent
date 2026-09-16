"""
Enaya Agent - Five-Layer Memory System
Session, Episodic, Semantic, Procedural, Project memory layers.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class MemoryEntry:
    """A memory entry with metadata."""
    id: str
    layer: str  # session, episodic, semantic, procedural, project
    content: str
    tags: list[str] = field(default_factory=list)
    importance: float = 1.0  # 0-1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    source: str = ""  # where this memory came from


class FiveLayerMemory:
    """
    Five-layer memory system:
    1. Session - Current conversation context
    2. Episodic - Specific events/interactions
    3. Semantic - General knowledge/facts
    4. Procedural - Skills/how-to knowledge
    5. Project - Codebase/project-specific knowledge
    """

    def __init__(self, profile: str = "default", project_path: str = None):
        self.profile = profile
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self._init_databases()

    def _init_databases(self) -> None:
        """Initialize SQLite databases for each layer."""
        import os
        enaya_home = Path(os.environ.get("ENAYA_HOME", Path.home() / ".enaya"))
        if self.profile != "default":
            enaya_home = enaya_home / "profiles" / self.profile

        self.memory_dir = enaya_home / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # One database per layer
        self._dbs = {}
        for layer in ["session", "episodic", "semantic", "procedural", "project"]:
            db_path = self.memory_dir / f"{layer}.db"
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            self._init_layer_table(conn, layer)
            self._dbs[layer] = conn

        # Project memory uses project-specific path
        if self.project_path:
            project_db = self.project_path / ".enaya" / "project_memory.db"
            project_db.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(project_db, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            self._init_layer_table(conn, "project")
            self._dbs["project"] = conn

    def _init_layer_table(self, conn: sqlite3.Connection, layer: str) -> None:
        """Initialize table for a memory layer."""
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {layer}_memory (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                tags TEXT,  -- JSON array
                importance REAL DEFAULT 1.0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                source TEXT DEFAULT ''
            )
        """)
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{layer}_tags ON {layer}_memory(tags)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{layer}_importance ON {layer}_memory(importance)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{layer}_created ON {layer}_memory(created_at)")

    def store(
        self,
        layer: str,
        content: str,
        tags: list[str] = None,
        importance: float = 1.0,
        source: str = "",
        entry_id: str = None,
    ) -> str:
        """Store a memory entry in a layer."""
        import uuid
        entry_id = entry_id or str(uuid.uuid4())[:12]
        now = datetime.now().timestamp()
        tags_json = json.dumps(tags or [])

        conn = self._dbs.get(layer)
        if not conn:
            raise ValueError(f"Unknown layer: {layer}")

        conn.execute(f"""
            INSERT INTO {layer}_memory (id, content, tags, importance, created_at, updated_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (entry_id, content, tags_json, importance, now, now, source))
        conn.commit()
        return entry_id

    def retrieve(
        self,
        layer: str,
        query: str = None,
        tags: list[str] = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        """Retrieve memories from a layer."""
        conn = self._dbs.get(layer)
        if not conn:
            raise ValueError(f"Unknown layer: {layer}")

        sql = f"SELECT * FROM {layer}_memory WHERE importance >= ?"
        params = [min_importance]

        if tags:
            # Simple tag matching (JSON contains)
            for tag in tags:
                sql += " AND tags LIKE ?"
                params.append(f'%"{tag}"%')

        sql += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(sql, params)
        results = []
        for row in cursor:
            results.append(MemoryEntry(
                id=row[0],
                layer=layer,
                content=row[1],
                tags=json.loads(row[2]) if row[2] else [],
                importance=row[3],
                created_at=datetime.fromtimestamp(row[4]),
                updated_at=datetime.fromtimestamp(row[5]),
                access_count=row[6],
                source=row[7] or "",
            ))
        return results

    def update_access(self, layer: str, entry_id: str) -> None:
        """Update access count and timestamp."""
        conn = self._dbs.get(layer)
        if not conn:
            return
        now = datetime.now().timestamp()
        conn.execute(f"""
            UPDATE {layer}_memory
            SET access_count = access_count + 1, updated_at = ?
            WHERE id = ?
        """, (now, entry_id))
        conn.commit()

    def delete(self, layer: str, entry_id: str) -> bool:
        """Delete a memory entry."""
        conn = self._dbs.get(layer)
        if not conn:
            return False
        cursor = conn.execute(f"DELETE FROM {layer}_memory WHERE id = ?", (entry_id,))
        conn.commit()
        return cursor.rowcount > 0

    def get_stats(self) -> dict:
        """Get statistics for all layers."""
        stats = {}
        for layer, conn in self._dbs.items():
            cursor = conn.execute(f"SELECT COUNT(*), AVG(importance) FROM {layer}_memory")
            count, avg_imp = cursor.fetchone()
            stats[layer] = {
                "count": count or 0,
                "avg_importance": avg_imp or 0,
            }
        return stats

    def close(self) -> None:
        """Close all database connections."""
        for conn in self._dbs.values():
            conn.close()


# =============================================================================
# Convenience Functions
# =============================================================================

def create_memory_system(profile: str = "default", project_path: str = None) -> FiveLayerMemory:
    """Create a five-layer memory system."""
    return FiveLayerMemory(profile=profile, project_path=project_path)
