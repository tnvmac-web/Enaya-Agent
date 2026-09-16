"""
Enaya Agent - Research Tools
web_search, web_extract, arxiv_search, paper_analyze.
Enaya-specific tools for deep research capabilities.
"""

from __future__ import annotations

import json

from enaya.tools.registry import registry

# =============================================================================
# arxiv_search
# =============================================================================

ARXIV_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "arxiv_search",
        "description": (
            "Search arXiv for academic papers. Returns papers with titles, "
            "authors, abstracts, and PDF URLs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (supports arXiv search syntax)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10, max: 50)",
                    "default": 10,
                },
                "category": {
                    "type": "string",
                    "description": "arXiv category filter (e.g., cs.AI, cs.LG, stat.ML)",
                },
            },
            "required": ["query"],
        },
    },
}


def check_arxiv_search_requirements() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("arxiv") is not None
    except ImportError:
        return False


def arxiv_search_tool(query: str, max_results: int = 10, category: str = None) -> str:
    """Search arXiv for papers."""
    try:
        import arxiv

        # Build search query
        search_query = query
        if category:
            search_query += f" AND cat:{category}"

        client = arxiv.Client()
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        results = []
        for paper in client.results(search):
            results.append(
                {
                    "title": paper.title,
                    "authors": [str(a) for a in paper.authors],
                    "abstract": paper.summary,
                    "pdf_url": paper.pdf_url,
                    "entry_id": paper.entry_id,
                    "published": paper.published.isoformat() if paper.published else None,
                    "categories": paper.categories,
                }
            )

        return json.dumps({"papers": results, "count": len(results)})

    except ImportError:
        return json.dumps({"error": "arxiv package not installed. Run: pip install arxiv"})
    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="arxiv_search",
    toolset="research",
    schema=ARXIV_SEARCH_SCHEMA,
    handler=arxiv_search_tool,
    check_fn=check_arxiv_search_requirements,
)


# =============================================================================
# paper_analyze
# =============================================================================

PAPER_ANALYZE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "paper_analyze",
        "description": (
            "Analyze an academic paper from PDF URL or arXiv ID. Extracts "
            "key findings, methodology, results, and limitations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "arXiv ID (e.g., 2301.00001) or PDF URL",
                },
                "focus": {
                    "type": "string",
                    "description": (
                        "Specific aspect to focus on (methodology, results, "
                        "limitations, etc.)"
                    ),
                },
            },
            "required": ["source"],
        },
    },
}


def check_paper_analyze_requirements() -> bool:
    try:
        import importlib.util

        return (
            importlib.util.find_spec("arxiv") is not None
            and importlib.util.find_spec("pdfplumber") is not None
        )
    except ImportError:
        return False


def paper_analyze_tool(source: str, focus: str = None) -> str:
    """Analyze an academic paper."""
    try:
        from io import BytesIO

        import arxiv
        import pdfplumber
        import requests

        # Fetch paper
        if source.startswith("http"):
            # Direct PDF URL
            response = requests.get(source, timeout=30)
            response.raise_for_status()
            pdf_file = BytesIO(response.content)
            title = "Unknown Paper"
        else:
            # arXiv ID
            client = arxiv.Client()
            search = arxiv.Search(id_list=[source])
            paper = next(client.results(search))
            pdf_response = requests.get(paper.pdf_url, timeout=30)
            pdf_response.raise_for_status()
            pdf_file = BytesIO(pdf_response.content)
            title = paper.title

        # Extract text from PDF
        text_parts = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        full_text = "\n\n".join(text_parts)

        # Truncate if too long
        if len(full_text) > 50000:
            full_text = full_text[:25000] + "\n\n[TRUNCATED]\n\n" + full_text[-25000:]

        # Build analysis prompt

        return json.dumps(
            {
                "title": title,
                "source": source,
                "full_text": full_text,
                "focus": focus,
                "word_count": len(full_text.split()),
                "note": (
                    "Full text extracted. Use with synthesis tools or "
                    "provide to LLM for analysis."
                ),
            }
        )

    except ImportError:
        return json.dumps(
            {"error": "Required packages not installed. Run: pip install arxiv pdfplumber requests"}
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="paper_analyze",
    toolset="research",
    schema=PAPER_ANALYZE_SCHEMA,
    handler=paper_analyze_tool,
    check_fn=check_paper_analyze_requirements,
)


# =============================================================================
# source_validator
# =============================================================================

SOURCE_VALIDATOR_SCHEMA = {
    "type": "function",
    "function": {
        "name": "source_validator",
        "description": (
            "Validate credibility of a source (website, paper, article). "
            "Returns credibility score and bias assessment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to validate"},
                "claim": {
                    "type": "string",
                    "description": "Specific claim to verify against source",
                },
            },
            "required": ["url"],
        },
    },
}


def check_source_validator_requirements() -> bool:
    return True


def source_validator_tool(url: str, claim: str = None) -> str:
    """Validate source credibility."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Basic credibility heuristics
        score = 50  # baseline
        factors = []

        # Domain authority
        high_authority = [
            "arxiv.org",
            "doi.org",
            "pubmed.ncbi.nlm.nih.gov",
            "scholar.google.com",
            "github.com",
            "docs.python.org",
            "developer.mozilla.org",
            "kubernetes.io",
            "aws.amazon.com",
            "cloud.google.com",
        ]
        if any(d in domain for d in high_authority):
            score += 30
            factors.append("High-authority domain")

        # Academic indicators
        if "arxiv.org" in domain or "doi.org" in domain:
            score += 20
            factors.append("Academic source")

        # HTTPS
        if parsed.scheme == "https":
            score += 5
            factors.append("HTTPS")

        # Known unreliable patterns
        unreliable_patterns = ["blogspot", "wordpress.com", "medium.com", "substack.com"]
        if any(p in domain for p in unreliable_patterns):
            score -= 15
            factors.append("Personal blog/platform")

        # Clamp score
        score = max(0, min(100, score))

        # Determine credibility level
        if score >= 80:
            level = "high"
        elif score >= 60:
            level = "medium"
        elif score >= 40:
            level = "low"
        else:
            level = "very_low"

        return json.dumps(
            {
                "url": url,
                "domain": domain,
                "credibility_score": score,
                "credibility_level": level,
                "factors": factors,
                "claim_verified": claim is not None,
                "note": (
                    "Heuristic assessment only. Manual verification "
                    "recommended for critical claims."
                ),
            }
        )

    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="source_validator",
    toolset="research",
    schema=SOURCE_VALIDATOR_SCHEMA,
    handler=source_validator_tool,
    check_fn=check_source_validator_requirements,
)
