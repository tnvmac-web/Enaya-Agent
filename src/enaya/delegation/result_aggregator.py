"""
Enaya Agent - Result Aggregator
Collect and synthesize subagent results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from enaya.delegation.orchestrator import DelegationOrchestrator


@dataclass
class AggregatedResult:
    """Aggregated result from multiple subagents."""
    query: str
    subagent_results: list[dict] = field(default_factory=list)
    synthesis: str | None = None
    conflicts: list[dict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


class ResultAggregator:
    """
    Collect, deduplicate, and synthesize results from subagents.
    """

    def __init__(self, orchestrator: DelegationOrchestrator):
        self.orchestrator = orchestrator

    def collect(self, subagent_ids: list[str] = None) -> list[dict]:
        """Collect raw results from completed subagents."""
        return self.orchestrator.collect_results(subagent_ids)

    def deduplicate(self, results: list[dict]) -> list[dict]:
        """Remove duplicate findings across results."""
        seen = set()
        unique = []
        for r in results:
            # Simple deduplication by content hash
            content_hash = hash(r.get("result", "")[:200])
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(r)
        return unique

    def detect_conflicts(self, results: list[dict]) -> list[dict]:
        """Detect conflicting information across results."""
        # This is a simplified version - real implementation would use LLM
        conflicts = []
        # Group by topic/task
        by_topic = {}
        for r in results:
            topic = r.get("task", "unknown")
            if topic not in by_topic:
                by_topic[topic] = []
            by_topic[topic].append(r)

        for topic, topic_results in by_topic.items():
            if len(topic_results) > 1:
                # Check for contradictions (simplified)
                contents = [r.get("result", "") for r in topic_results]
                if len(set(contents)) > 1:
                    conflicts.append({
                        "topic": topic,
                        "positions": [{"subagent_id": r["subagent_id"], "summary": c[:200]} for r, c in zip(topic_results, contents)],
                    })

        return conflicts

    def synthesize(
        self,
        query: str,
        results: list[dict],
        conflict_resolution: str = "consensus",
    ) -> AggregatedResult:
        """Synthesize results into a coherent answer."""
        # Deduplicate
        unique_results = self.deduplicate(results)

        # Detect conflicts
        conflicts = self.detect_conflicts(unique_results)

        # Build synthesis prompt (for LLM)
        synthesis_prompt = self._build_synthesis_prompt(query, unique_results, conflicts, conflict_resolution)

        aggregated = AggregatedResult(
            query=query,
            subagent_results=unique_results,
            conflicts=conflicts,
            synthesis=synthesis_prompt,  # Placeholder - LLM would fill this
        )

        return aggregated

    def _build_synthesis_prompt(
        self,
        query: str,
        results: list[dict],
        conflicts: list[dict],
        conflict_resolution: str,
    ) -> str:
        """Build prompt for LLM to synthesize results."""
        prompt = f"""Synthesize the following subagent results into a comprehensive answer for: {query}

Subagent Results:
"""
        for i, r in enumerate(results):
            prompt += f"\n--- Subagent {r['subagent_id']} ---\nTask: {r['task']}\nResult: {r['result']}\n"

        if conflicts:
            prompt += "\nConflicts Detected:\n"
            for c in conflicts:
                prompt += f"- {c['topic']}: {len(c['positions'])} differing positions\n"

        prompt += f"\nConflict Resolution Strategy: {conflict_resolution}\n"
        prompt += "\nProvide a synthesized answer with citations to subagent IDs."

        return prompt
