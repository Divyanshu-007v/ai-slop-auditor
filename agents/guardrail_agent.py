"""
Guardrail / Human-in-the-Loop Agent — enforces safety rules.

Agent Role: Prevent unsafe or overconfident outputs. Flag claims for
            human review when confidence is insufficient.
Agent Skill: safety_check
Input: Verdict + Claim
Output: Verdict (with guardrail adjustments applied)

Demonstrates: Security Guardrails, Human-in-the-Loop review.
"""

from __future__ import annotations

import logging

from models import Claim, ClaimType, RiskLevel, Verdict, VerdictLabel

logger = logging.getLogger(__name__)


# Domain-specific disclaimers
_DISCLAIMERS = {
    ClaimType.MEDICAL: (
        "⚕️ MEDICAL DISCLAIMER: This system does not provide medical advice. "
        "Consult a qualified healthcare professional for medical questions."
    ),
    ClaimType.FINANCIAL: (
        "💰 FINANCIAL DISCLAIMER: This system does not provide financial advice. "
        "Consult a qualified financial advisor before making investment decisions."
    ),
    ClaimType.POLITICAL: (
        "🏛️ POLITICAL CONTENT NOTE: Political claims may involve nuance, context, "
        "and evolving situations. Independent verification is strongly recommended."
    ),
}


class GuardrailAgent:
    """
    Agent Role: Enforce safety rules on every verdict.
    Agent Skill: safety_check
    Input: Verdict + Claim
    Output: Verdict (modified if guardrails triggered)

    Rules enforced:
      1. trust_score < 85 → human_review_required = True
      2. No evidence → verdict = "Insufficient Evidence"
      3. No citations → verdict = "Insufficient Evidence"
      4. High-risk domain + weak evidence → human_review_required = True
      5. Contradictory evidence → human_review_required = True
      6. Never give medical, legal, or financial advice
      7. Never hallucinate sources or generate fake citations
      8. Frame output as auditing assistant, not final authority
    """

    name: str = "guardrail_agent"
    description: str = "Enforces safety rules and flags claims for human review"

    def apply_guardrails(self, verdict: Verdict, claim: Claim) -> Verdict:
        """
        Apply guardrail rules to a verdict.

        May modify the verdict label, trust score, human_review_required,
        and risk_notes fields based on safety rules.

        Args:
            verdict: The verdict from the Consensus Agent.
            claim: The original claim being evaluated.

        Returns:
            Modified Verdict with guardrail adjustments applied.
        """
        # Work with a copy of risk_notes to avoid mutation issues
        risk_notes = list(verdict.risk_notes)
        human_review = verdict.human_review_required
        verdict_label = verdict.verdict

        # Rule 1: Low trust score → flag for human review
        if verdict.trust_score < 85:
            human_review = True
            if verdict.trust_score < 50:
                risk_notes.append(
                    f"Low trust score ({verdict.trust_score}/100). "
                    f"Claim requires careful verification."
                )

        # Rule 2: No evidence → Insufficient Evidence
        if not verdict.evidence_used:
            verdict_label = VerdictLabel.INSUFFICIENT_EVIDENCE
            human_review = True
            risk_notes.append("No evidence was retrieved for this claim.")

        # Rule 3: No citations → Insufficient Evidence
        if not verdict.citations:
            verdict_label = VerdictLabel.INSUFFICIENT_EVIDENCE
            human_review = True
            risk_notes.append("No citations available to support the verdict.")

        # Rule 4: High-risk domain with weak evidence
        high_risk = {ClaimType.MEDICAL, ClaimType.FINANCIAL, ClaimType.POLITICAL}
        if claim.claim_type in high_risk:
            # Always flag high-risk domains unless strongly supported
            if verdict.trust_score < 90:
                human_review = True

            # Add domain-specific disclaimer
            disclaimer = _DISCLAIMERS.get(claim.claim_type)
            if disclaimer and disclaimer not in risk_notes:
                risk_notes.append(disclaimer)

            # Check for weak evidence in high-risk domain
            if verdict.trust_score < 60:
                risk_notes.append(
                    f"⚠️ HIGH RISK: {claim.claim_type.value.title()} claim "
                    f"with weak evidence (score: {verdict.trust_score}/100). "
                    f"Professional verification strongly recommended."
                )

        # Rule 5: Contradictory evidence
        if verdict.evidence_used:
            supporting = sum(1 for e in verdict.evidence_used if e.supports_claim)
            contradicting = sum(1 for e in verdict.evidence_used if e.contradicts_claim)
            if supporting > 0 and contradicting > 0:
                human_review = True
                risk_notes.append(
                    f"Evidence is contradictory: {supporting} supporting vs "
                    f"{contradicting} contradicting sources."
                )

        # Rule 6: Never overstate certainty
        if verdict_label == VerdictLabel.SUPPORTED and verdict.trust_score < 90:
            # Downgrade from Supported to Mostly Supported if score isn't very high
            verdict_label = VerdictLabel.MOSTLY_SUPPORTED

        # Rule 7: Add general disclaimer
        general_disclaimer = (
            "This is an automated audit result. This system is an auditing "
            "assistant, not a final authority. Results should be independently "
            "verified."
        )
        if general_disclaimer not in risk_notes:
            risk_notes.append(general_disclaimer)

        # Build updated verdict
        updated = Verdict(
            claim_id=verdict.claim_id,
            claim_text=verdict.claim_text,
            verdict=verdict_label,
            trust_score=verdict.trust_score,
            human_review_required=human_review,
            reasoning=verdict.reasoning,
            evidence_used=verdict.evidence_used,
            citations=verdict.citations,
            risk_notes=risk_notes,
        )

        logger.info(
            "Guardrails applied to %s: verdict=%s, human_review=%s, notes=%d",
            claim.claim_id,
            verdict_label.value,
            human_review,
            len(risk_notes),
        )

        return updated
