"""
Tests for no-evidence scenarios.

Verifies that:
  - Claims with zero evidence get "Insufficient Evidence"
  - No fake citations are generated
  - Report generation works with no-evidence claims
  - Session memory stores claims even with no evidence
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.consensus_agent import ConsensusAgent
from agents.guardrail_agent import GuardrailAgent
from agents.report_agent import ReportAgent
from memory.session_memory import SessionMemory
from models import Claim, ClaimType, Evidence, RiskLevel, Verdict, VerdictLabel


def _make_claim(text="Unknown unverifiable claim"):
    return Claim(
        claim_id="C1", claim_text=text, claim_type=ClaimType.GENERAL,
        risk_level=RiskLevel.LOW,
    )


class TestNoEvidenceVerdict:
    """Test that claims with no evidence get Insufficient Evidence."""

    def test_consensus_no_evidence(self):
        agent = ConsensusAgent()
        claim = _make_claim()
        verdict = agent.adjudicate(claim, [])
        assert verdict.verdict == VerdictLabel.INSUFFICIENT_EVIDENCE
        assert verdict.trust_score == 0.0
        assert verdict.human_review_required is True

    def test_guardrail_no_evidence(self):
        agent = GuardrailAgent()
        verdict = Verdict(
            claim_id="C1",
            claim_text="Test",
            verdict=VerdictLabel.PARTIALLY_SUPPORTED,
            trust_score=50,
            evidence_used=[],
            citations=[],
        )
        claim = _make_claim()
        result = agent.apply_guardrails(verdict, claim)
        assert result.verdict == VerdictLabel.INSUFFICIENT_EVIDENCE


class TestNoCitationGenerated:
    """Test that no fake citations are generated."""

    def test_no_evidence_no_citations(self):
        agent = ConsensusAgent()
        claim = _make_claim()
        verdict = agent.adjudicate(claim, [])
        assert len(verdict.citations) == 0

    def test_empty_evidence_no_citations(self):
        agent = ConsensusAgent()
        claim = _make_claim("A claim about nothing specific")
        verdict = agent.adjudicate(claim, [])
        assert verdict.citations == []


class TestReportWithNoEvidence:
    """Test report generation works with no-evidence claims."""

    def test_report_generation_no_evidence(self):
        agent = ReportAgent()
        verdict = Verdict(
            claim_id="C1",
            claim_text="An unverifiable claim",
            verdict=VerdictLabel.INSUFFICIENT_EVIDENCE,
            trust_score=0,
            human_review_required=True,
            reasoning="No evidence found.",
            evidence_used=[],
            citations=[],
        )
        report = agent.generate_report([verdict], "test-session")
        assert report.total_claims == 1
        assert report.insufficient_evidence_claims == 1
        assert len(report.markdown_report) > 0

    def test_report_empty_verdicts(self):
        agent = ReportAgent()
        report = agent.generate_report([], "test-session")
        assert report.total_claims == 0
        assert len(report.markdown_report) > 0


class TestSessionMemoryNoEvidence:
    """Test that session memory stores claims even with no evidence."""

    def test_store_no_evidence_claim(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            memory = SessionMemory(db_path)

            session_id = memory.create_session("test input")
            claim = _make_claim()
            verdict = Verdict(
                claim_id="C1", claim_text="Test", verdict=VerdictLabel.INSUFFICIENT_EVIDENCE,
                trust_score=0, evidence_used=[], citations=[],
            )

            memory.store_claim_result(session_id, "C1", claim, [], verdict)
            memory.complete_session(session_id, 1)

            session = memory.get_session(session_id)
            assert session is not None
            assert len(session["claims"]) == 1
            assert session["total_claims"] == 1
