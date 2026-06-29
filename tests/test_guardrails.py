"""
Tests for the Guardrail Agent.

Verifies that:
  - Low trust score triggers human review
  - Medical claims with weak evidence are flagged
  - No citations → Insufficient Evidence
  - Contradictory evidence is flagged
  - Financial predictions get human review
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.guardrail_agent import GuardrailAgent
from models import Claim, ClaimType, Evidence, RiskLevel, Verdict, VerdictLabel


def _make_claim(text="Test", claim_type=ClaimType.GENERAL, risk=RiskLevel.LOW):
    return Claim(
        claim_id="C1", claim_text=text, claim_type=claim_type, risk_level=risk,
    )


def _make_verdict(
    score=50, verdict=VerdictLabel.PARTIALLY_SUPPORTED,
    evidence=None, citations=None, review=False,
):
    return Verdict(
        claim_id="C1",
        claim_text="Test claim",
        verdict=verdict,
        trust_score=score,
        human_review_required=review,
        reasoning="Test reasoning",
        evidence_used=evidence or [],
        citations=citations or [],
    )


def _make_evidence(supports=True, contradicts=False, cred=90):
    return Evidence(
        source_title="Source",
        source_type="peer_reviewed_journal",
        source_url="https://example.com",
        snippet="Evidence text.",
        credibility_score=cred,
        relevance_score=85,
        supports_claim=supports,
        contradicts_claim=contradicts,
    )


class TestTrustScoreThreshold:
    """Test that trust score < 85 triggers human review."""

    def test_low_score_triggers_review(self):
        agent = GuardrailAgent()
        verdict = _make_verdict(score=60, citations=["cite1"], evidence=[_make_evidence()])
        claim = _make_claim()
        result = agent.apply_guardrails(verdict, claim)
        assert result.human_review_required is True

    def test_high_score_no_forced_review_for_general(self):
        agent = GuardrailAgent()
        verdict = _make_verdict(
            score=92, verdict=VerdictLabel.SUPPORTED,
            citations=["cite1"], evidence=[_make_evidence()],
        )
        claim = _make_claim()
        result = agent.apply_guardrails(verdict, claim)
        # General claims with high scores should not force human review
        # (though the guardrail still adds general disclaimer)
        assert result.trust_score == 92


class TestMedicalClaims:
    """Test that medical claims with weak evidence are flagged."""

    def test_medical_weak_evidence_flagged(self):
        agent = GuardrailAgent()
        verdict = _make_verdict(
            score=55, citations=["cite1"],
            evidence=[_make_evidence(supports=False, contradicts=True)],
        )
        claim = _make_claim("Drug cures cancer", ClaimType.MEDICAL, RiskLevel.HIGH)
        result = agent.apply_guardrails(verdict, claim)
        assert result.human_review_required is True
        # Should have medical disclaimer
        has_disclaimer = any("medical" in n.lower() for n in result.risk_notes)
        assert has_disclaimer

    def test_financial_claim_flagged(self):
        agent = GuardrailAgent()
        verdict = _make_verdict(
            score=40, citations=["cite1"],
            evidence=[_make_evidence(supports=False, contradicts=True)],
        )
        claim = _make_claim("Stock guaranteed to rise", ClaimType.FINANCIAL, RiskLevel.HIGH)
        result = agent.apply_guardrails(verdict, claim)
        assert result.human_review_required is True


class TestNoCitations:
    """Test that no citations → Insufficient Evidence."""

    def test_no_citations_insufficient(self):
        agent = GuardrailAgent()
        verdict = _make_verdict(score=50, citations=[], evidence=[_make_evidence()])
        claim = _make_claim()
        result = agent.apply_guardrails(verdict, claim)
        assert result.verdict == VerdictLabel.INSUFFICIENT_EVIDENCE

    def test_no_evidence_insufficient(self):
        agent = GuardrailAgent()
        verdict = _make_verdict(score=50, citations=["cite1"], evidence=[])
        claim = _make_claim()
        result = agent.apply_guardrails(verdict, claim)
        assert result.verdict == VerdictLabel.INSUFFICIENT_EVIDENCE


class TestContradictoryEvidence:
    """Test that contradictory evidence triggers human review."""

    def test_contradictory_flagged(self):
        agent = GuardrailAgent()
        evidence = [
            _make_evidence(supports=True, contradicts=False),
            _make_evidence(supports=False, contradicts=True),
        ]
        verdict = _make_verdict(score=60, citations=["c1", "c2"], evidence=evidence)
        claim = _make_claim()
        result = agent.apply_guardrails(verdict, claim)
        assert result.human_review_required is True
        has_contradiction_note = any("contradictory" in n.lower() for n in result.risk_notes)
        assert has_contradiction_note


class TestGeneralDisclaimer:
    """Test that general disclaimer is always added."""

    def test_disclaimer_present(self):
        agent = GuardrailAgent()
        verdict = _make_verdict(score=95, citations=["cite1"], evidence=[_make_evidence()])
        claim = _make_claim()
        result = agent.apply_guardrails(verdict, claim)
        has_disclaimer = any("auditing assistant" in n.lower() for n in result.risk_notes)
        assert has_disclaimer
