"""
Core data models for the AI-Slop & Misinformation Auditor.

All agents share these Pydantic models as their input/output contracts.
This ensures consistent data flow across the entire pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ClaimType(str, Enum):
    """Categories of factual claims the system can classify."""
    MEDICAL = "medical"
    FINANCIAL = "financial"
    POLITICAL = "political"
    SCIENCE = "science"
    GENERAL = "general"
    STATISTICS = "statistics"


class VerdictLabel(str, Enum):
    """Allowed verdict labels for claim adjudication."""
    SUPPORTED = "Supported"
    MOSTLY_SUPPORTED = "Mostly Supported"
    PARTIALLY_SUPPORTED = "Partially Supported"
    UNSUPPORTED = "Unsupported"
    CONTRADICTED = "Contradicted"
    INSUFFICIENT_EVIDENCE = "Insufficient Evidence"
    NEEDS_HUMAN_REVIEW = "Needs Human Review"


class RiskLevel(str, Enum):
    """Risk level assigned to a claim based on its domain."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ---------------------------------------------------------------------------
# Claim Model
# ---------------------------------------------------------------------------

class Claim(BaseModel):
    """
    A single factual claim extracted from user input text.
    
    Produced by the Extraction Agent.
    Consumed by the Retrieval Agent and Consensus Agent.
    """
    claim_id: str = Field(default_factory=lambda: f"C{uuid.uuid4().hex[:6].upper()}")
    claim_text: str = Field(..., description="The exact factual claim text")
    claim_type: ClaimType = Field(default=ClaimType.GENERAL, description="Category of the claim")
    entities: list[str] = Field(default_factory=list, description="Key entities mentioned in the claim")
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Risk level based on claim domain")
    time_sensitivity: str = Field(default="low", description="How time-sensitive this claim is: high, medium, low")
    needs_evidence: bool = Field(default=True, description="Whether this claim requires evidence retrieval")


# ---------------------------------------------------------------------------
# Evidence Model
# ---------------------------------------------------------------------------

class Evidence(BaseModel):
    """
    A single piece of evidence retrieved for a claim.
    
    Produced by the Retrieval Agent (via MCP tools).
    Consumed by the Consensus Agent.
    """
    source_title: str = Field(..., description="Title of the evidence source")
    source_type: str = Field(default="unknown", description="Type of source: peer_reviewed_journal, medical_database, etc.")
    source_url: str = Field(default="", description="URL of the source (empty if local fixture)")
    snippet: str = Field(..., description="Relevant excerpt from the source")
    published_date: str = Field(default="", description="Publication date (ISO format if available)")
    credibility_score: float = Field(default=50.0, ge=0, le=100, description="Source credibility score 0-100")
    relevance_score: float = Field(default=50.0, ge=0, le=100, description="Relevance of this evidence to the claim 0-100")
    supports_claim: bool = Field(default=False, description="Does this evidence support the claim?")
    contradicts_claim: bool = Field(default=False, description="Does this evidence contradict the claim?")


# ---------------------------------------------------------------------------
# Verdict Model
# ---------------------------------------------------------------------------

class Verdict(BaseModel):
    """
    The adjudication result for a single claim.
    
    Produced by the Consensus Agent, refined by the Guardrail Agent.
    """
    claim_id: str
    claim_text: str
    verdict: VerdictLabel = Field(default=VerdictLabel.INSUFFICIENT_EVIDENCE)
    trust_score: float = Field(default=0.0, ge=0, le=100, description="Overall trust score 0-100")
    human_review_required: bool = Field(default=False)
    reasoning: str = Field(default="", description="Explanation of the verdict")
    evidence_used: list[Evidence] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list, description="List of citation strings")
    risk_notes: list[str] = Field(default_factory=list, description="Risk/safety notes from guardrail checks")

    @staticmethod
    def compute_trust_score(
        source_credibility_score: float,
        evidence_agreement_score: float,
        recency_score: float,
        claim_specificity_score: float,
        citation_quality_score: float,
    ) -> float:
        """
        Compute the weighted trust score using the official formula.
        
        Formula:
            trust_score = 0.35 * source_credibility
                        + 0.30 * evidence_agreement
                        + 0.15 * recency
                        + 0.10 * claim_specificity
                        + 0.10 * citation_quality
        
        All input scores should be 0-100. Output is clamped to 0-100.
        """
        score = (
            0.35 * source_credibility_score
            + 0.30 * evidence_agreement_score
            + 0.15 * recency_score
            + 0.10 * claim_specificity_score
            + 0.10 * citation_quality_score
        )
        return max(0.0, min(100.0, round(score, 1)))

    @staticmethod
    def score_to_verdict_label(score: float) -> VerdictLabel:
        """
        Map a trust score to a verdict label.
        
        Score interpretation:
            90-100: Supported
            75-89:  Mostly Supported
            50-74:  Partially Supported
            25-49:  Unsupported
            0-24:   Contradicted
        """
        if score >= 90:
            return VerdictLabel.SUPPORTED
        elif score >= 75:
            return VerdictLabel.MOSTLY_SUPPORTED
        elif score >= 50:
            return VerdictLabel.PARTIALLY_SUPPORTED
        elif score >= 25:
            return VerdictLabel.UNSUPPORTED
        else:
            return VerdictLabel.CONTRADICTED


# ---------------------------------------------------------------------------
# Audit Report Model
# ---------------------------------------------------------------------------

class AuditReport(BaseModel):
    """
    The final audit report aggregating all verdicts.
    
    Produced by the Report Agent.
    Displayed in the Streamlit UI and exported as Markdown/JSON.
    """
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    input_text_preview: str = Field(default="", description="First 200 chars of input text")
    
    # Summary statistics
    total_claims: int = 0
    supported_claims: int = 0
    mostly_supported_claims: int = 0
    partially_supported_claims: int = 0
    unsupported_claims: int = 0
    contradicted_claims: int = 0
    insufficient_evidence_claims: int = 0
    human_review_claims: int = 0
    
    # Detailed results
    verdicts: list[Verdict] = Field(default_factory=list)
    
    # Report content
    markdown_report: str = Field(default="", description="Full Markdown report text")
    risk_summary: str = Field(default="", description="Overall risk assessment")
    limitations: str = Field(
        default="This system is an auditing assistant, not a final authority. "
        "Results should be verified by domain experts. The system does not "
        "provide medical, legal, or financial advice.",
        description="Limitations disclaimer"
    )
    
    # Extraction mode used
    extraction_mode: str = Field(default="rule-based", description="'rule-based' or 'gemini-llm'")
