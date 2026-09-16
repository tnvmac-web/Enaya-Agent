"""
Enaya Agent - Source Validator
Credibility scoring and bias detection for sources.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CredibilityAssessment:
    """Credibility assessment of a source."""

    url: str
    domain: str
    score: float  # 0-100
    level: str  # high, medium, low, very_low
    factors: list[str]
    bias_indicators: list[str]
    claim_verified: bool = False


class SourceValidator:
    """
    Validates source credibility and detects bias.
    """

    def __init__(self, agent):
        self.agent = agent

    def validate(self, url: str, claim: str = None) -> CredibilityAssessment:
        """Validate a source's credibility."""
        # Use agent's source_validator tool
        result = self.agent.execute_tool(
            {
                "function": {
                    "name": "source_validator",
                    "arguments": {"url": url, "claim": claim or ""},
                },
                "id": "source_validator_1",
            },
            task_id="source_validation",
        )

        import json

        try:
            data = json.loads(result)
            return CredibilityAssessment(
                url=data.get("url", url),
                domain=data.get("domain", ""),
                score=data.get("credibility_score", 50),
                level=data.get("credibility_level", "medium"),
                factors=data.get("factors", []),
                bias_indicators=[],
                claim_verified=data.get("claim_verified", False),
            )
        except Exception:
            return CredibilityAssessment(
                url=url,
                domain="",
                score=50,
                level="medium",
                factors=["parse_error"],
                bias_indicators=[],
            )

    def batch_validate(self, urls: list[str]) -> list[CredibilityAssessment]:
        """Validate multiple sources."""
        return [self.validate(url) for url in urls]
