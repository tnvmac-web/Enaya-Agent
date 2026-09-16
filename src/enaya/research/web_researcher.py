"""
Enaya Agent - Web Researcher
Web search + extraction pipeline for deep research.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResearchSource:
    """A research source with metadata."""
    url: str
    title: str
    content: str
    credibility_score: float = 0.0
    source_type: str = "web"  # web, academic, paper
    extracted_at: str = ""


class WebResearcher:
    """
    Orchestrates web research: search -> extract -> validate -> summarize.
    """

    def __init__(self, agent):
        self.agent = agent

    def research(self, query: str, depth: str = "deep", sources: str = "all") -> dict:
        """
        Conduct research on a query.
        Returns structured findings with citations.
        """
        # This would use the agent's tools to do actual research
        # For now, return a template
        return {
            "query": query,
            "depth": depth,
            "sources": sources,
            "status": "template_only",
            "note": "Use agent's web_search, web_extract, arxiv_search tools directly",
        }


def quick_research(query: str, agent) -> str:
    """Quick research using web search only."""
    prompt = f"Research this query and provide a concise answer with sources: {query}"
    return agent.run_conversation(prompt)


def deep_research(query: str, agent, max_sources: int = 10) -> str:
    """Deep research with multiple sources and synthesis."""
    prompt = f"""Conduct deep research on: {query}

Process:
1. Search for relevant sources (web + academic)
2. Extract content from top {max_sources} sources
3. Validate source credibility
4. Synthesize findings with citations
5. Identify gaps and conflicts

Provide a comprehensive research report."""
    return agent.run_conversation(prompt)
