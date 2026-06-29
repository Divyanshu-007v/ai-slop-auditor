"""
Tests for the Consensus Agent scoring and verdict logic.

Verifies that:
  - Trust score formula computes correctly
  - Score ranges map to correct verdicts
  - Strong evidence → Supported
  - No evidence → Insufficient Evidence
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.consensus_agent import ConsensusAgent
from models import Claim, ClaimType, Evidence, RiskLevel, Verdict, VerdictLabel


def _make_claim(text="Test claim", claim_type=ClaimType.GENERAL):
    return Claim(
        claim_id="C1",
        claim_text=text,
        claim_type=claim_type,
        entities=["test"],
        risk_level=RiskLevel.LOW,
    )


def _make_evidence(supports=True, contradicts=False, credibility=90, relevance=90):
    return Evidence(
        source_title="Test Source",
        source_type="peer_reviewed_journal",
        source_url="https://example.com/test",
        snippet="Test evidence snippet.",
        published_date="2024-06-01",
        credibility_score=credibility,
        relevance_score=relevance,
        supports_claim=supports,
        contradicts_claim=contradicts,
    )


class TestTrustScoreFormula:
    """Test the weighted trust score computation."""

    def test_perfect_scores(self):
        score = Verdict.compute_trust_score(100, 100, 100, 100, 100)
        assert score == 100.0

    def test_zero_scores(self):
        score = Verdict.compute_trust_score(0, 0, 0, 0, 0)
        assert score == 0.0

    def test_weighted_computation(self):
        score = Verdict.compute_trust_score(
            source_credibility_score=80,
            evidence_agreement_score=70,
            recency_score=60,
            claim_specificity_score=50,
            citation_quality_score=40,
        )
        expected = 0.35 * 80 + 0.30 * 70 + 0.15 * 60 + 0.10 * 50 + 0.10 * 40
        assert abs(score - expected) < 0.2

    def test_score_clamped_to_range(self):
        score = Verdict.compute_trust_score(100, 100, 100, 100, 100)
        assert 0 <= score <= 100


class TestVerdictMapping:
    """Test score-to-verdict label mapping."""

    def test_high_score_supported(self):
        label = Verdict.score_to_verdict_label(95)
        assert label == VerdictLabel.SUPPORTED

    def test_mostly_supported_range(self):
        label = Verdict.score_to_verdict_label(80)
        assert label == VerdictLabel.MOSTLY_SUPPORTED

    def test_partially_supported_range(self):
        label = Verdict.score_to_verdict_label(60)
        assert label == VerdictLabel.PARTIALLY_SUPPORTED

    def test_unsupported_range(self):
        label = Verdict.score_to_verdict_label(30)
        assert label == VerdictLabel.UNSUPPORTED

    def test_contradicted_range(self):
        label = Verdict.score_to_verdict_label(10)
        assert label == VerdictLabel.CONTRADICTED


class TestConsensusAgent:
    """Test the full consensus agent adjudication."""

    def test_strong_evidence_supported(self):
        agent = ConsensusAgent()
        claim = _make_claim("Drinking water prevents dehydration.")
        evidence = [
            _make_evidence(supports=True, credibility=95, relevance=97),
            _make_evidence(supports=True, credibility=96, relevance=95),
        ]
        verdict = agent.adjudicate(claim, evidence)
        assert verdict.trust_score >= 70
        assert verdict.verdict in {
            VerdictLabel.SUPPORTED,
            VerdictLabel.MOSTLY_SUPPORTED,
            VerdictLabel.PARTIALLY_SUPPORTED,
        }

    def test_no_evidence_insufficient(self):
        agent = ConsensusAgent()
        claim = _make_claim("Random unverifiable claim.")
        verdict = agent.adjudicate(claim, [])
        assert verdict.verdict == VerdictLabel.INSUFFICIENT_EVIDENCE
        assert verdict.human_review_required is True
        assert verdict.trust_score == 0.0

    def test_contradicting_evidence_low_score(self):
        agent = ConsensusAgent()
        claim = _make_claim("Coffee cures diabetes.")
        evidence = [
            _make_evidence(supports=False, contradicts=True, credibility=92),
            _make_evidence(supports=False, contradicts=True, credibility=95),
        ]
        verdict = agent.adjudicate(claim, evidence)
        assert verdict.trust_score < 50

    def test_citations_generated(self):
        agent = ConsensusAgent()
        claim = _make_claim("Test claim")
        evidence = [_make_evidence()]
        verdict = agent.adjudicate(claim, evidence)
        assert len(verdict.citations) >= 1

    def test_reasoning_not_empty(self):
        agent = ConsensusAgent()
        claim = _make_claim("Test claim")
        evidence = [_make_evidence()]
        verdict = agent.adjudicate(claim, evidence)
        assert len(verdict.reasoning) > 0
