"""
Enaya Agent - Semantic Store
ChromaDB integration for vector-based semantic memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SemanticEntry:
    """An entry in the semantic store."""
    id: str
    content: str
    embedding: list[float] = None
    metadata: dict = None
    collection: str = "default"


class SemanticStore:
    """
    Vector-based semantic memory using ChromaDB.
    Stores embeddings for semantic search across sessions.
    """

    def __init__(self, profile: str = "default", persist_dir: str = None):
        self.profile = profile
        self.client = None
        self.collections = {}
        self._init_client(persist_dir)

    def _init_client(self, persist_dir: str = None) -> None:
        """Initialize ChromaDB client."""
        try:
            import chromadb
            from chromadb.config import Settings

            if persist_dir is None:
                import os
                from pathlib import Path
                enaya_home = Path(os.environ.get("ENAYA_HOME", Path.home() / ".enaya"))
                if self.profile != "default":
                    enaya_home = enaya_home / "profiles" / self.profile
                persist_dir = str(enaya_home / "chroma")

            self.client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )

            # Create default collections
            self._get_collection("semantic")
            self._get_collection("episodic")
            self._get_collection("procedural")

        except ImportError:
            # ChromaDB not installed
            self.client = None

    def _get_collection(self, name: str):
        """Get or create a collection."""
        if not self.client:
            return None
        if name not in self.collections:
            self.collections[name] = self.client.get_or_create_collection(name=name)
        return self.collections[name]

    def add(
        self,
        content: str,
        collection: str = "semantic",
        metadata: dict = None,
        entry_id: str = None,
    ) -> str:
        """Add content to semantic store."""
        if not self.client:
            return "chromadb_not_available"

        import uuid
        entry_id = entry_id or str(uuid.uuid4())[:12]

        coll = self._get_collection(collection)
        if coll:
            coll.add(
                documents=[content],
                metadatas=[metadata or {}],
                ids=[entry_id],
            )
        return entry_id

    def search(
        self,
        query: str,
        collection: str = "semantic",
        n_results: int = 5,
        filter_metadata: dict = None,
    ) -> list[dict]:
        """Semantic search."""
        if not self.client:
            return []

        coll = self._get_collection(collection)
        if not coll:
            return []

        results = coll.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_metadata,
        )

        # Format results
        formatted = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "id": results["ids"][0][i],
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })
        return formatted

    def delete(self, entry_id: str, collection: str = "semantic") -> bool:
        """Delete an entry."""
        if not self.client:
            return False

        coll = self._get_collection(collection)
        if coll:
            try:
                coll.delete(ids=[entry_id])
                return True
            except:
                return False
        return False

    def get_stats(self) -> dict:
        """Get collection statistics."""
        if not self.client:
            return {"status": "chromadb_not_available"}

        stats = {}
        for name, coll in self.collections.items():
            try:
                stats[name] = {"count": coll.count()}
            except:
                stats[name] = {"count": 0}
        return stats