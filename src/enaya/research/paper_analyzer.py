"""
Enaya Agent - Paper Analyzer
Academic paper processing and structured extraction.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PaperAnalysis:
    """Structured analysis of an academic paper."""

    title: str
    authors: list[str]
    abstract: str
    methodology: str = ""
    key_findings: list[str] = None
    limitations: list[str] = None
    implications: str = ""
    citations: list[str] = None
    confidence: float = 0.0


class PaperAnalyzer:
    """
    Analyzes academic papers from PDF or arXiv.
    Extracts structured information for synthesis.
    """

    def __init__(self, agent):
        self.agent = agent

    def analyze(self, source: str, focus: str = None) -> PaperAnalysis:
        """Analyze a paper and return structured analysis."""
        # Use agent's paper_analyze tool
        result = self.agent.execute_tool(
            {
                "function": {
                    "name": "paper_analyze",
                    "arguments": {"source": source, "focus": focus or ""},
                },
                "id": "paper_analyze_1",
            },
            task_id="paper_analysis",
        )

        # Parse and structure
        import json

        try:
            data = json.loads(result)
            return PaperAnalysis(
                title=data.get("title", "Unknown"),
                authors=[],
                abstract=data.get("full_text", "")[:500],
            )
        except Exception:
            return PaperAnalysis(title="Error", authors=[], abstract=str(result))

    def extract_key_points(self, paper_text: str) -> dict:
        """Extract key points from paper text."""
        return {
            "methodology": "",
            "findings": [],
            "limitations": [],
            "implications": "",
        }
