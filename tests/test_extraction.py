"""
Tests for the Claim Extraction Agent.

Verifies that:
  - Opinions are filtered out
  - Factual claims are extracted
  - Claim types are correctly classified
  - Entities are extracted
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.extraction_agent import ExtractionAgent
from models import ClaimType, RiskLevel


def _agent():
    """Create an extraction agent (rule-based mode)."""
    return ExtractionAgent()


class TestOpinionFiltering:
    """Test that opinions and non-factual statements are filtered out."""

    def test_opinion_i_think(self):
        agent = _agent()
        claims = agent.extract_claims("I think the weather is nice today.")
        claim_texts = [c.claim_text.lower() for c in claims]
        assert not any("i think" in t for t in claim_texts)

    def test_opinion_i_feel(self):
        agent = _agent()
        claims = agent.extract_claims("I feel like this is a bad idea.")
        claim_texts = [c.claim_text.lower() for c in claims]
        assert not any("i feel" in t for t in claim_texts)

    def test_opinion_personally(self):
        agent = _agent()
        claims = agent.extract_claims("Personally, I believe crypto is the future.")
        claim_texts = [c.claim_text.lower() for c in claims]
        assert not any("personally" in t for t in claim_texts)

    def test_question_filtered(self):
        agent = _agent()
        claims = agent.extract_claims("Is Bitcoin going to crash?")
        assert len(claims) == 0

    def test_mixed_text_filters_opinions(self):
        agent = _agent()
        text = (
            "I think coffee is great. "
            "Coffee cures diabetes according to a new study. "
            "Honestly, this is amazing news."
        )
        claims = agent.extract_claims(text)
        # Should extract the factual claim but not the opinions
        factual = [c for c in claims if "cures" in c.claim_text.lower() or "study" in c.claim_text.lower()]
        opinions = [c for c in claims if "i think" in c.claim_text.lower() or "honestly" in c.claim_text.lower()]
        assert len(opinions) == 0


class TestFactualExtraction:
    """Test that factual claims are correctly extracted."""

    def test_extracts_factual_claim(self):
        agent = _agent()
        claims = agent.extract_claims(
            "Apple launched Vision Pro in February 2024."
        )
        assert len(claims) >= 1
        assert any("vision pro" in c.claim_text.lower() or "apple" in c.claim_text.lower() for c in claims)

    def test_extracts_medical_claim(self):
        agent = _agent()
        claims = agent.extract_claims(
            "Vaccines do not cause autism according to CDC research."
        )
        assert len(claims) >= 1

    def test_empty_input(self):
        agent = _agent()
        claims = agent.extract_claims("")
        assert len(claims) == 0

    def test_whitespace_input(self):
        agent = _agent()
        claims = agent.extract_claims("   \n\n   ")
        assert len(claims) == 0


class TestClaimClassification:
    """Test that claims are classified by the correct type."""

    def test_medical_classification(self):
        agent = _agent()
        claims = agent.extract_claims("Coffee cures diabetes according to new research.")
        medical_claims = [c for c in claims if c.claim_type == ClaimType.MEDICAL]
        assert len(medical_claims) >= 1

    def test_financial_classification(self):
        agent = _agent()
        claims = agent.extract_claims(
            "Bitcoin is guaranteed to double in price next month according to analysts."
        )
        financial_claims = [c for c in claims if c.claim_type == ClaimType.FINANCIAL]
        assert len(financial_claims) >= 1

    def test_medical_gets_high_risk(self):
        agent = _agent()
        claims = agent.extract_claims("This drug cures cancer in 90% of patients.")
        for c in claims:
            if c.claim_type == ClaimType.MEDICAL:
                assert c.risk_level == RiskLevel.HIGH


class TestEntityExtraction:
    """Test that entities are extracted from claims."""

    def test_extracts_proper_nouns(self):
        agent = _agent()
        claims = agent.extract_claims("Apple launched Vision Pro in February 2024.")
        if claims:
            all_entities = []
            for c in claims:
                all_entities.extend([e.lower() for e in c.entities])
            # Should find at least some entities
            assert len(all_entities) >= 1

    def test_extracts_numbers(self):
        agent = _agent()
        claims = agent.extract_claims("The company's stock rose 40% after the announcement.")
        if claims:
            all_entities = []
            for c in claims:
                all_entities.extend(c.entities)
            has_number = any("40" in e for e in all_entities)
            assert has_number
