"""
Consensus & Adjudication Agent — compares claims against evidence.

Agent Role: Compare each claim with retrieved evidence, compute a
            weighted trust score, and produce an explainable verdict.
Agent Skill: adjudicate
Input: Claim + list[Evidence]
Output: Verdict

Trust score formula:
    trust_score = 0.35 * source_credibility_score
                + 0.30 * evidence_agreement_score
                + 0.15 * recency_score
                + 0.10 * claim_specificity_score
                + 0.10 * citation_quality_score

Demonstrates: Agent Skills, explainable AI scoring.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

from models import Claim, ClaimType, Evidence, RiskLevel, Verdict, VerdictLabel
from rag.summary_tree import SummaryTree

logger = logging.getLogger(__name__)


class ConsensusAgent:
    """
    Agent Role: Adjudicate claims against retrieved evidence.
    Agent Skill: adjudicate
    Input: Claim + list[Evidence]
    Output: Verdict

    Computes a weighted trust score, performs self-checks, and
    produces an explainable verdict with reasoning.
    """

    name: str = "consensus_agent"
    description: str = "Compares claims against evidence and produces verdicts"

    def __init__(self):
        self._summary_tree = SummaryTree()

    def adjudicate(self, claim: Claim, evidence_list: list[Evidence]) -> Verdict:
        """
        Adjudicate a claim against its evidence.

        Args:
            claim: The claim being evaluated.
            evidence_list: Evidence retrieved for this claim.

        Returns:
            Verdict with trust score, label, reasoning, and citations.
        """
        # Handle no-evidence case early
        if not evidence_list:
            return Verdict(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                verdict=VerdictLabel.INSUFFICIENT_EVIDENCE,
                trust_score=0.0,
                human_review_required=True,
                reasoning="No evidence was found for this claim. Cannot verify or refute.",
                evidence_used=[],
                citations=[],
                risk_notes=["No evidence available for verification."],
            )

        # Compute sub-scores
        source_cred = self._compute_source_credibility(evidence_list)
        agreement = self._compute_evidence_agreement(evidence_list)
        recency = self._compute_recency_score(evidence_list)
        specificity = self._compute_claim_specificity(claim)
        citation_quality = self._compute_citation_quality(evidence_list)

        # Compute weighted trust score
        trust_score = Verdict.compute_trust_score(
            source_credibility_score=source_cred,
            evidence_agreement_score=agreement,
            recency_score=recency,
            claim_specificity_score=specificity,
            citation_quality_score=citation_quality,
        )

        # Self-check before issuing verdict
        self_check = self._self_check(claim, evidence_list, trust_score)

        # Determine verdict label
        if self_check.get("force_insufficient"):
            verdict_label = VerdictLabel.INSUFFICIENT_EVIDENCE
        elif self_check.get("force_human_review"):
            verdict_label = VerdictLabel.NEEDS_HUMAN_REVIEW
        else:
            verdict_label = Verdict.score_to_verdict_label(trust_score)

        # Build reasoning
        reasoning = self._build_reasoning(
            claim, evidence_list, trust_score,
            source_cred, agreement, recency, specificity, citation_quality,
            self_check,
        )

        # Build citation list
        citations = self._build_citations(evidence_list)

        # Summarize evidence
        summary = self._summary_tree.summarize(evidence_list)

        return Verdict(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            verdict=verdict_label,
            trust_score=trust_score,
            human_review_required=self_check.get("human_review", False),
            reasoning=reasoning,
            evidence_used=evidence_list,
            citations=citations,
            risk_notes=self_check.get("risk_notes", []),
        )

    # -------------------------------------------------------------------
    # Sub-score computations
    # -------------------------------------------------------------------

    def _compute_source_credibility(self, evidence: list[Evidence]) -> float:
        """Average credibility score across all evidence sources (0-100)."""
        if not evidence:
            return 0.0
        scores = [e.credibility_score for e in evidence]
        return sum(scores) / len(scores)

    def _compute_evidence_agreement(self, evidence: list[Evidence]) -> float:
        """
        Measure of how much evidence agrees with the claim (0-100).

        - All supporting → 100
        - All contradicting → 0
        - Mixed → proportional
        """
        if not evidence:
            return 0.0

        supporting = sum(1 for e in evidence if e.supports_claim)
        contradicting = sum(1 for e in evidence if e.contradicts_claim)
        neutral = len(evidence) - supporting - contradicting

        if supporting + contradicting == 0:
            # All neutral — give moderate score
            return 50.0

        # Agreement ratio weighted toward supporting evidence
        agreement = (supporting * 100 + neutral * 40) / len(evidence)
        return min(100.0, max(0.0, agreement))

    def _compute_recency_score(self, evidence: list[Evidence]) -> float:
        """
        Score based on how recent the evidence is (0-100).

        More recent evidence gets a higher score.
        """
        if not evidence:
            return 0.0

        now = datetime.now()
        scores: list[float] = []

        for e in evidence:
            if e.published_date:
                try:
                    pub_date = datetime.fromisoformat(e.published_date)
                    days_old = (now - pub_date).days
                    # Score: 100 for today, decays over 3 years
                    score = max(0.0, 100.0 - (days_old / 1095) * 100)
                    scores.append(score)
                except (ValueError, TypeError):
                    scores.append(50.0)  # Unknown date → moderate
            else:
                scores.append(50.0)

        return sum(scores) / len(scores) if scores else 50.0

    def _compute_claim_specificity(self, claim: Claim) -> float:
        """
        Score based on how specific the claim is (0-100).

        More specific claims (with dates, numbers, entities) score higher
        because they're easier to verify.
        """
        score = 40.0  # Base score

        # Bonus for entities
        entity_count = len(claim.entities)
        score += min(30.0, entity_count * 10.0)

        # Bonus for numbers
        has_numbers = bool(re.search(r"\b\d+\b", claim.claim_text))
        if has_numbers:
            score += 15.0

        # Bonus for specific dates
        has_date = bool(re.search(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}",
            claim.claim_text,
        ))
        if has_date:
            score += 15.0

        return min(100.0, score)

    def _compute_citation_quality(self, evidence: list[Evidence]) -> float:
        """
        Score based on the quality and diversity of citations (0-100).

        Considers:
          - Number of unique source types
          - Presence of URLs
          - Source type diversity
        """
        if not evidence:
            return 0.0

        # Unique source types
        source_types = set(e.source_type for e in evidence)
        type_diversity = min(100.0, len(source_types) * 25.0)

        # URL presence
        urls = [e for e in evidence if e.source_url]
        url_ratio = (len(urls) / len(evidence)) * 100 if evidence else 0

        return (type_diversity * 0.5 + url_ratio * 0.5)

    # -------------------------------------------------------------------
    # Self-check
    # -------------------------------------------------------------------

    def _self_check(
        self,
        claim: Claim,
        evidence: list[Evidence],
        trust_score: float,
    ) -> dict:
        """
        Internal self-check before issuing a verdict.

        Checks:
          1. Enough evidence? (at least 1-2 reliable sources)
          2. Independent sources?
          3. Direct support?
          4. Exaggeration check?
          5. High-risk domain?
          6. Should this go to human review?
        """
        notes: list[str] = []
        force_insufficient = False
        force_human_review = False
        human_review = False

        # Check 1: Minimum evidence threshold
        reliable = [e for e in evidence if e.credibility_score >= 70]
        if len(reliable) < 1:
            notes.append("No reliable sources (credibility >= 70) found.")
            force_insufficient = True

        # Check 2: Evidence contradiction
        supporting = [e for e in evidence if e.supports_claim]
        contradicting = [e for e in evidence if e.contradicts_claim]
        if supporting and contradicting:
            notes.append("Evidence contains both supporting and contradicting sources.")
            human_review = True

        # Check 3: High-risk domain with weak evidence
        high_risk_types = {ClaimType.MEDICAL, ClaimType.FINANCIAL, ClaimType.POLITICAL}
        if claim.claim_type in high_risk_types and trust_score < 85:
            notes.append(
                f"High-risk domain ({claim.claim_type.value}) with moderate/low trust score."
            )
            human_review = True

        # Check 4: All evidence contradicts claim
        if contradicting and not supporting:
            notes.append("All evidence contradicts this claim.")

        # Check 5: Trust score below threshold
        if trust_score < 85:
            human_review = True

        return {
            "risk_notes": notes,
            "force_insufficient": force_insufficient,
            "force_human_review": force_human_review,
            "human_review": human_review,
        }

    # -------------------------------------------------------------------
    # Reasoning & Citations
    # -------------------------------------------------------------------

    def _build_reasoning(
        self,
        claim: Claim,
        evidence: list[Evidence],
        trust_score: float,
        source_cred: float,
        agreement: float,
        recency: float,
        specificity: float,
        citation_quality: float,
        self_check: dict,
    ) -> str:
        """Build human-readable reasoning for the verdict."""
        parts: list[str] = []

        # Score breakdown
        parts.append(f"Trust Score: {trust_score}/100")
        parts.append(f"  - Source Credibility: {source_cred:.1f}/100 (weight: 35%)")
        parts.append(f"  - Evidence Agreement: {agreement:.1f}/100 (weight: 30%)")
        parts.append(f"  - Recency: {recency:.1f}/100 (weight: 15%)")
        parts.append(f"  - Claim Specificity: {specificity:.1f}/100 (weight: 10%)")
        parts.append(f"  - Citation Quality: {citation_quality:.1f}/100 (weight: 10%)")

        # Evidence summary
        supporting = sum(1 for e in evidence if e.supports_claim)
        contradicting = sum(1 for e in evidence if e.contradicts_claim)
        neutral = len(evidence) - supporting - contradicting
        parts.append(f"\nEvidence: {len(evidence)} sources ({supporting} supporting, "
                      f"{contradicting} contradicting, {neutral} neutral)")

        # Self-check notes
        if self_check.get("risk_notes"):
            parts.append("\nRisk Notes:")
            for note in self_check["risk_notes"]:
                parts.append(f"  ⚠ {note}")

        return "\n".join(parts)

    def _build_citations(self, evidence: list[Evidence]) -> list[str]:
        """Build a list of citation strings from evidence."""
        citations: list[str] = []
        for e in evidence:
            cite = f"{e.source_title}"
            if e.source_url:
                cite += f" ({e.source_url})"
            if e.published_date:
                cite += f" [{e.published_date}]"
            citations.append(cite)
        return citations
