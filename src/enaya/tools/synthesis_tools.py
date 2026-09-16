"""
Enaya Agent - Synthesis Tools
synthesize_results, compare_sources, extract_claims.
Enaya-specific tools for result aggregation.
"""

from __future__ import annotations

import json

from enaya.tools.registry import registry

# =============================================================================
# synthesize_results
# =============================================================================

SYNTHESIZE_RESULTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "synthesize_results",
        "description": (
            "Synthesize multiple subagent results into a coherent answer. "
            "Handles deduplication, conflict resolution, and citation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "subagent_id": {"type": "string"},
                            "task": {"type": "string"},
                            "result": {"type": "string"},
                            "sources": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["subagent_id", "task", "result"],
                    },
                },
                "query": {"type": "string", "description": "Original query or goal"},
                "conflict_resolution": {
                    "type": "string",
                    "enum": ["latest", "consensus", "manual"],
                    "description": "How to handle conflicting information",
                    "default": "consensus",
                },
            },
            "required": ["results", "query"],
        },
    },
}


def check_synthesize_results_requirements() -> bool:
    return True


def synthesize_results_tool(
    results: list[dict], query: str, conflict_resolution: str = "consensus"
) -> str:
    """Synthesize multiple results into a coherent answer."""
    # This is a template - the LLM would do the actual synthesis
    return json.dumps(
        {
            "query": query,
            "num_results": len(results),
            "conflict_resolution": conflict_resolution,
            "synthesis_template": {
                "summary": "Executive summary of findings",
                "key_findings": [
                    {"finding": "Finding 1", "supporting_sources": [], "confidence": "high"},
                ],
                "conflicts": [
                    {"topic": "Topic", "positions": [], "resolution": ""},
                ],
                "gaps": ["Gap 1", "Gap 2"],
                "recommendations": ["Rec 1", "Rec 2"],
            },
            "instruction": (
                "Fill in the synthesis_template with actual synthesized content. "
                "Cite sources using subagent_id."
            ),
        }
    )


registry.register(
    name="synthesize_results",
    toolset="synthesis",
    schema=SYNTHESIZE_RESULTS_SCHEMA,
    handler=synthesize_results_tool,
    check_fn=check_synthesize_results_requirements,
)


# =============================================================================
# compare_sources
# =============================================================================

COMPARE_SOURCES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "compare_sources",
        "description": (
            "Compare multiple sources on the same topic. Returns structured comparison table."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "content": {"type": "string"},
                            "credibility": {"type": "number"},
                        },
                        "required": ["name", "content"],
                    },
                },
                "topic": {"type": "string", "description": "Topic to compare"},
                "dimensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Comparison dimensions",
                },
            },
            "required": ["sources", "topic"],
        },
    },
}


def check_compare_sources_requirements() -> bool:
    return True


def compare_sources_tool(sources: list[dict], topic: str, dimensions: list[str] = None) -> str:
    """Compare sources on a topic."""
    default_dimensions = ["accuracy", "completeness", "bias", "recency", "authority"]
    dimensions = dimensions or default_dimensions

    return json.dumps(
        {
            "topic": topic,
            "sources_compared": len(sources),
            "dimensions": dimensions,
            "comparison_template": {
                "table": [{"dimension": d, "source_scores": {}} for d in dimensions],
                "winner": "",
                "notes": "",
            },
            "instruction": "Fill in the comparison_template with actual scores and analysis.",
        }
    )


registry.register(
    name="compare_sources",
    toolset="synthesis",
    schema=COMPARE_SOURCES_SCHEMA,
    handler=compare_sources_tool,
    check_fn=check_compare_sources_requirements,
)


# =============================================================================
# extract_claims
# =============================================================================

EXTRACT_CLAIMS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "extract_claims",
        "description": "Extract verifiable claims from text with source attribution.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to extract claims from"},
                "source": {"type": "string", "description": "Source identifier"},
                "min_confidence": {
                    "type": "number",
                    "description": "Minimum confidence threshold (0-1)",
                    "default": 0.5,
                },
            },
            "required": ["text", "source"],
        },
    },
}


def check_extract_claims_requirements() -> bool:
    return True


def extract_claims_tool(text: str, source: str, min_confidence: float = 0.5) -> str:
    """Extract claims from text."""
    # Template for LLM to fill
    return json.dumps(
        {
            "source": source,
            "text_length": len(text),
            "min_confidence": min_confidence,
            "claims_template": [
                {
                    "claim": "Extracted claim",
                    "evidence": "Supporting text from source",
                    "confidence": 0.8,
                    "claim_type": "factual|opinion|prediction|speculation",
                }
            ],
            "instruction": (
                "Extract all verifiable claims from the text. Return filled claims_template."
            ),
        }
    )


registry.register(
    name="extract_claims",
    toolset="synthesis",
    schema=EXTRACT_CLAIMS_SCHEMA,
    handler=extract_claims_tool,
    check_fn=check_extract_claims_requirements,
)
