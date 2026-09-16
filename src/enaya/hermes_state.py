"""
Enaya Agent - Session Storage
SQLite with FTS5 full-text search.
Mirrors Hermes Agent's hermes_state.py exactly.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class SessionStore:
    """
    Session persistence with SQLite + FTS5.
    - Lineage tracking (parent/child across compressions)
    - Per-profile isolation
    - Atomic writes with contention handling
    """

    def __init__(self, profile: str = "default"):
        self.profile = profile
        self._db_path = self._get_db_path()
        self._local = threading.local()
        self._init_db()

    def _get_db_path(self) -> Path:
        """Get database path for profile."""
        import os
        enaya_home = Path(os.environ.get("ENAYA_HOME", Path.home() / ".enaya"))
        if self.profile != "default":
            enaya_home = enaya_home / "profiles" / self.profile
        enaya_home.mkdir(parents=True, exist_ok=True)
        return enaya_home / "state.db"

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=30.0,
            )
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    @contextmanager
    def _transaction(self):
        """Transaction context manager with retry logic."""
        conn = self._get_connection()
        max_retries = 3
        for attempt in range(max_retries):
            try:
                yield conn
                conn.commit()
                return
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                raise

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._transaction() as conn:
            # Sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    profile TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    chat_type TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    parent_session_id TEXT,
                    lineage_id TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    token_count INTEGER DEFAULT 0
                )
            """)

            # Messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_call_id TEXT,
                    display_kind TEXT,
                    row_id INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)

            # FTS5 virtual table for full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    session_id UNINDEXED,
                    role UNINDEXED,
                    content,
                    tool_call_id UNINDEXED,
                    row_id UNINDEXED,
                    content_rowid=id,
                    tokenize='porter unicode61'
                )
            """)

            # FTS triggers for automatic sync
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
                    INSERT INTO messages_fts (rowid, session_id, role, content, tool_call_id, row_id)
                    VALUES (new.id, new.session_id, new.role, new.content, new.tool_call_id, new.row_id);
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages BEGIN
                    DELETE FROM messages_fts WHERE rowid = old.id;
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages BEGIN
                    DELETE FROM messages_fts WHERE rowid = old.id;
                    INSERT INTO messages_fts (rowid, session_id, role, content, tool_call_id, row_id)
                    VALUES (new.id, new.session_id, new.role, new.content, new.tool_call_id, new.row_id);
                END
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_profile ON sessions(profile)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_lineage ON sessions(lineage_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_row_id ON messages(session_id, row_id)")

    # =============================================================================
    # Session Operations
    # =============================================================================

    def create_session(
        self,
        session_id: str,
        platform: str = "cli",
        chat_type: str = "private",
        chat_id: str = "local",
        parent_session_id: str | None = None,
        lineage_id: str | None = None,
    ) -> None:
        """Create a new session."""
        now = time.time()
        lineage = lineage_id or session_id

        with self._transaction() as conn:
            conn.execute("""
                INSERT INTO sessions (id, profile, platform, chat_type, chat_id, created_at, updated_at, parent_session_id, lineage_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, self.profile, platform, chat_type, chat_id, now, now, parent_session_id, lineage))

    def save_session(self, session_id: str, messages: list[dict]) -> None:
        """Save conversation history to session."""
        now = time.time()

        with self._transaction() as conn:
            # Upsert session
            conn.execute("""
                INSERT INTO sessions (id, profile, platform, chat_type, chat_id, created_at, updated_at, lineage_id, message_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    message_count = excluded.message_count
            """, (session_id, self.profile, "cli", "private", "local", now, now, session_id, len(messages)))

            # Clear existing messages for this session
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))

            # Insert messages
            for row_id, msg in enumerate(messages):
                content = msg.get("content", "")
                if isinstance(content, list):
                    content = json.dumps(content)

                conn.execute("""
                    INSERT INTO messages (session_id, role, content, tool_call_id, display_kind, row_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    msg.get("role", "user"),
                    content,
                    msg.get("tool_call_id"),
                    msg.get("display_kind"),
                    row_id,
                    now,
                ))

    def load_session(self, session_id: str) -> list[dict] | None:
        """Load conversation history from session."""
        with self._transaction() as conn:
            cursor = conn.execute("""
                SELECT role, content, tool_call_id, display_kind, row_id
                FROM messages
                WHERE session_id = ?
                ORDER BY row_id ASC
            """, (session_id,))

            messages = []
            for row in cursor:
                content = row["content"]
                # Try to parse JSON content (for cached system prompts with cache_control)
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, list):
                        content = parsed
                except (json.JSONDecodeError, TypeError):
                    pass

                msg = {
                    "role": row["role"],
                    "content": content,
                    "row_id": row["row_id"],
                }
                if row["tool_call_id"]:
                    msg["tool_call_id"] = row["tool_call_id"]
                if row["display_kind"]:
                    msg["display_kind"] = row["display_kind"]

                messages.append(msg)

            return messages if messages else None

    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        with self._transaction() as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            # Messages deleted via CASCADE

    def list_sessions(self, limit: int = 50) -> list[dict]:
        """List recent sessions for this profile."""
        with self._transaction() as conn:
            cursor = conn.execute("""
                SELECT id, platform, chat_type, chat_id, created_at, updated_at, message_count, token_count
                FROM sessions
                WHERE profile = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (self.profile, limit))

            return [dict(row) for row in cursor]

    def get_session_info(self, session_id: str) -> dict | None:
        """Get session metadata."""
        with self._transaction() as conn:
            cursor = conn.execute("""
                SELECT id, profile, platform, chat_type, chat_id, created_at, updated_at,
                       parent_session_id, lineage_id, message_count, token_count
                FROM sessions
                WHERE id = ?
            """, (session_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    # =============================================================================
    # Search Operations
    # =============================================================================

    def search_messages(self, query: str, limit: int = 20) -> list[dict]:
        """Full-text search across all sessions."""
        with self._transaction() as conn:
            cursor = conn.execute("""
                SELECT m.session_id, m.role, m.content, m.row_id, s.updated_at
                FROM messages_fts fts
                JOIN messages m ON m.id = fts.rowid
                JOIN sessions s ON s.id = m.session_id
                WHERE fts.content MATCH ? AND s.profile = ?
                ORDER BY s.updated_at DESC
                LIMIT ?
            """, (query, self.profile, limit))

            return [dict(row) for row in cursor]

    # =============================================================================
    # Lineage Operations
    # =============================================================================

    def get_lineage(self, lineage_id: str) -> list[dict]:
        """Get all sessions in a lineage (parent -> children)."""
        with self._transaction() as conn:
            cursor = conn.execute("""
                SELECT id, parent_session_id, created_at, updated_at, message_count
                FROM sessions
                WHERE lineage_id = ?
                ORDER BY created_at ASC
            """, (lineage_id,))

            return [dict(row) for row in cursor]

    def get_children(self, parent_session_id: str) -> list[dict]:
        """Get child sessions (from compression)."""
        with self._transaction() as conn:
            cursor = conn.execute("""
                SELECT id, created_at, updated_at, message_count
                FROM sessions
                WHERE parent_session_id = ?
                ORDER BY created_at ASC
            """, (parent_session_id,))

            return [dict(row) for row in cursor]

    # =============================================================================
    # Maintenance
    # =============================================================================

    def vacuum(self) -> None:
        """Vacuum database to reclaim space."""
        with self._transaction() as conn:
            conn.execute("VACUUM")

    def get_stats(self) -> dict:
        """Get database statistics."""
        with self._transaction() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM sessions WHERE profile = ?", (self.profile,))
            session_count = cursor.fetchone()["count"]

            cursor = conn.execute("SELECT COUNT(*) as count FROM messages WHERE session_id IN (SELECT id FROM sessions WHERE profile = ?)", (self.profile,))
            message_count = cursor.fetchone()["count"]

            # Database size
            db_size = self._db_path.stat().st_size if self._db_path.exists() else 0

            return {
                "profile": self.profile,
                "sessions": session_count,
                "messages": message_count,
                "db_size_bytes": db_size,
                "db_path": str(self._db_path),
            }

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# =============================================================================
# Convenience Functions
# =============================================================================

def build_session_key(profile: str, platform: str, chat_type: str, chat_id: str) -> str:
    """Build standardized session key."""
    return f"agent:{profile}:{platform}:{chat_type}:{chat_id}"


def parse_session_key(key: str) -> dict:
    """Parse session key into components."""
    parts = key.split(":", 4)
    if len(parts) != 5 or parts[0] != "agent":
        raise ValueError(f"Invalid session key: {key}")
    return {
        "profile": parts[1],
        "platform": parts[2],
        "chat_type": parts[3],
        "chat_id": parts[4],
    }
