"""
Enaya Agent - Project Indexer
Codebase knowledge graph indexing using codebase-memory-mcp patterns.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class ProjectIndex:
    """Indexed project information."""
    path: str
    nodes: int = 0
    edges: int = 0
    languages: dict[str, int] = None
    indexed_at: str = ""
    status: str = "pending"


class ProjectIndexer:
    """
    Indexes codebase for project-level memory.
    Uses codebase-memory-mcp binary if available, falls back to basic analysis.
    """

    def __init__(self, project_path: str = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.index_dir = self.project_path / ".enaya" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.mcp_binary = self._find_mcp_binary()

    def _find_mcp_binary(self) -> Optional[str]:
        """Find codebase-memory-mcp binary."""
        candidates = [
            "codebase-memory-mcp",
            "codebase-memory-mcp.exe",
            str(Path.home() / "AppData" / "Local" / "Programs" / "codebase-memory-mcp" / "codebase-memory-mcp.exe"),
            "/usr/local/bin/codebase-memory-mcp",
        ]
        for c in candidates:
            try:
                result = subprocess.run([c, "--version"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return c
            except:
                continue
        return None

    def index(self, force: bool = False) -> ProjectIndex:
        """Index the project."""
        index_file = self.index_dir / "index.json"

        if index_file.exists() and not force:
            with open(index_file) as f:
                data = json.load(f)
            return ProjectIndex(**data)

        if self.mcp_binary:
            return self._index_with_mcp()
        else:
            return self._index_basic()

    def _index_with_mcp(self) -> ProjectIndex:
        """Index using codebase-memory-mcp."""
        try:
            # Run indexer
            result = subprocess.run(
                [self.mcp_binary, "index", str(self.project_path), "--output", str(self.index_dir)],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                index_file = self.index_dir / "index.json"
                if index_file.exists():
                    with open(index_file) as f:
                        data = json.load(f)
                    return ProjectIndex(**data)

            # Fallback
            return self._index_basic()

        except Exception:
            return self._index_basic()

    def _index_basic(self) -> ProjectIndex:
        """Basic indexing without MCP."""
        from datetime import datetime
        import fnmatch

        languages = {}
        nodes = 0
        edges = 0

        # Count files by language
        extensions = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React",
            ".tsx": "React TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".go": "Go",
            ".rs": "Rust",
            ".cs": "C#",
            ".php": "PHP",
            ".rb": "Ruby",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".md": "Markdown",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
        }

        for root, dirs, files in os.walk(self.project_path):
            # Skip common ignore dirs
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["node_modules", "__pycache__", "venv", "env", "dist", "build", ".git"]]

            for file in files:
                ext = Path(file).suffix.lower()
                if ext in extensions:
                    lang = extensions[ext]
                    languages[lang] = languages.get(lang, 0) + 1
                    nodes += 1

        index = ProjectIndex(
            path=str(self.project_path),
            nodes=nodes,
            edges=edges,
            languages=languages,
            indexed_at=datetime.now().isoformat(),
            status="basic" if not self.mcp_binary else "mcp",
        )

        # Save index
        index_file = self.index_dir / "index.json"
        with open(index_file, "w") as f:
            json.dump({
                "path": index.path,
                "nodes": index.nodes,
                "edges": index.edges,
                "languages": index.languages,
                "indexed_at": index.indexed_at,
                "status": index.status,
            }, f, indent=2)

        return index

    def query(self, query: str, limit: int = 10) -> list[dict]:
        """Query the project index."""
        if self.mcp_binary:
            try:
                result = subprocess.run(
                    [self.mcp_binary, "query", str(self.project_path), query, "--limit", str(limit)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    return json.loads(result.stdout)
            except:
                pass

        # Basic fallback
        return [{"note": "MCP not available - install codebase-memory-mcp for code queries"}]

    def get_stats(self) -> dict:
        """Get index statistics."""
        index = self.index(force=False)
        return {
            "path": index.path,
            "nodes": index.nodes,
            "edges": index.edges,
            "languages": index.languages,
            "indexed_at": index.indexed_at,
            "status": index.status,
            "mcp_available": self.mcp_binary is not None,
        }