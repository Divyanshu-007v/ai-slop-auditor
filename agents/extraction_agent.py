"""
Claim Extraction Agent — extracts factual, verifiable claims from text.

Agent Role: Extract factual claims from messy input text (articles,
            transcripts, social media posts).
Agent Skill: claim_extract
Input: Raw text string
Output: List of Claim objects

Supports two modes:
  - Rule-based (offline default): Always available, no API keys needed.
  - Gemini LLM (optional): Activated when GOOGLE_API_KEY is set in env.

Demonstrates: ADK-style agent architecture, Agent Skills.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

from models import Claim, ClaimType, RiskLevel
from rag.chunker import chunk_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword dictionaries for rule-based classification
# ---------------------------------------------------------------------------

_MEDICAL_KEYWORDS = {
    "cure", "cures", "treat", "treatment", "therapy", "vaccine", "vaccines",
    "drug", "medication", "symptom", "disease", "cancer", "diabetes",
    "health", "doctor", "hospital", "clinical", "patient", "diagnosis",
    "surgery", "antibiotic", "virus", "infection", "immune", "FDA",
    "pharmaceutical", "medicine", "medical", "autism", "dehydration",
    "blood", "heart", "brain", "lung", "kidney", "liver",
}

_FINANCIAL_KEYWORDS = {
    "stock", "stocks", "bitcoin", "crypto", "cryptocurrency", "invest",
    "investment", "market", "trading", "price", "profit", "loss",
    "portfolio", "fund", "bond", "interest", "rate", "inflation",
    "economy", "GDP", "revenue", "earnings", "dividend", "IPO",
    "SEC", "federal reserve", "bank", "loan", "mortgage", "guaranteed",
    "double", "triple", "return", "bull", "bear", "crash",
}

_POLITICAL_KEYWORDS = {
    "president", "congress", "senate", "election", "vote", "policy",
    "government", "law", "legislation", "democrat", "republican",
    "political", "politician", "campaign", "regulation", "mandate",
    "supreme court", "executive order", "immigration", "border",
    "military", "war", "diplomat", "sanction", "treaty",
}

_SCIENCE_KEYWORDS = {
    "study", "research", "scientist", "experiment", "hypothesis",
    "theory", "evidence", "data", "peer-reviewed", "journal",
    "discovery", "physics", "chemistry", "biology", "evolution",
    "climate", "temperature", "carbon", "earth", "planet", "space",
    "NASA", "genome", "DNA", "RNA", "quantum", "atom", "molecule",
    "billion years", "million years", "radiometric",
}

# Phrases that indicate an opinion, not a factual claim
_OPINION_INDICATORS = [
    r"\bi think\b", r"\bi feel\b", r"\bi believe\b", r"\bin my opinion\b",
    r"\bpersonally\b", r"\bhonestly\b", r"\bprobably\b", r"\bmaybe\b",
    r"\bperhaps\b", r"\bmight be\b", r"\bcould be\b", r"\bseems like\b",
    r"\bi guess\b", r"\bwho knows\b", r"\bjust my\b", r"\bthat's just\b",
    r"\bi love\b", r"\bi hate\b", r"\bso sick of\b", r"\bamazing\b",
    r"\bincredible\b", r"\binsane\b", r"\bcrazy\b",
]

# Patterns to filter out non-claims
_FILTER_PATTERNS = [
    r"^(hey|hi|hello|welcome|thanks|thank you|bye|goodbye)\b",  # greetings
    r"^(like|subscribe|share|comment|follow|click)\b",  # social media CTAs
    r"(like and subscribe|drop a comment|make sure to|don't forget)",
    r"^(anyway|anyways|so yeah|lol|lmao|haha)\b",  # filler
    r"^#\w+",  # hashtags
    r"^@\w+",  # mentions
    r"^🔥|^🚨|^💯|^👀",  # emoji-only starts
]


class ExtractionAgent:
    """
    Agent Role: Extract factual, verifiable claims from messy text.
    Agent Skill: claim_extract
    Input: Raw text (str)
    Output: list[Claim]

    Ignores: opinions, emotions, jokes, vague predictions, insults,
             marketing hype, personal preferences, questions.

    Extracts: claims with dates, numbers, medical claims, financial claims,
              political claims, scientific claims, factual statements.
    """

    name: str = "extraction_agent"
    description: str = "Extracts factual claims from text input"

    def __init__(self):
        """Initialize the Extraction Agent."""
        self._gemini_available = False
        self._gemini_model = None
        self._check_gemini()

    def _check_gemini(self) -> None:
        """Check if Gemini API is available for enhanced extraction."""
        api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self._gemini_model = genai.GenerativeModel("gemini-2.0-flash")
                self._gemini_available = True
                logger.info("Gemini LLM available for enhanced extraction")
            except Exception as e:
                logger.warning("Gemini setup failed, falling back to rule-based: %s", e)
                self._gemini_available = False
        else:
            logger.info("No GOOGLE_API_KEY found — using rule-based extraction")

    @property
    def extraction_mode(self) -> str:
        """Return current extraction mode."""
        return "gemini-llm" if self._gemini_available else "rule-based"

    def extract_claims(self, text: str) -> list[Claim]:
        """
        Extract factual claims from input text.

        Uses Gemini LLM if available, otherwise falls back to rule-based extraction.

        Args:
            text: Raw input text (article, transcript, social post).

        Returns:
            List of extracted Claim objects.
        """
        if not text or not text.strip():
            return []

        # Use Gemini if available
        if self._gemini_available:
            try:
                claims = self._extract_with_gemini(text)
                if claims:
                    logger.info("Gemini extracted %d claims", len(claims))
                    return claims
                logger.warning("Gemini extraction returned empty, falling back to rule-based")
            except Exception as e:
                logger.warning("Gemini extraction failed, falling back to rule-based: %s", e)

        # Rule-based extraction (always available)
        return self._extract_rule_based(text)

    # -------------------------------------------------------------------
    # Rule-based extraction (offline default)
    # -------------------------------------------------------------------

    def _extract_rule_based(self, text: str) -> list[Claim]:
        """
        Extract claims using rule-based heuristics.

        Process:
          1. Chunk long texts
          2. Split into sentences
          3. Filter out opinions, questions, filler
          4. Classify remaining sentences as claims
          5. Assign type, risk, entities
        """
        # Chunk long texts
        chunks = chunk_text(text, chunk_size=2000, overlap=100)
        all_text = " ".join(chunks) if len(chunks) > 1 else text

        # Split into sentences
        sentences = self._split_sentences(all_text)

        # Filter and extract claims
        claims: list[Claim] = []
        claim_counter = 0

        for sentence in sentences:
            sentence = sentence.strip()

            # Skip very short or very long sentences
            if len(sentence) < 15 or len(sentence) > 500:
                continue

            # Skip opinions
            if self._is_opinion(sentence):
                continue

            # Skip questions
            if sentence.strip().endswith("?"):
                continue

            # Skip filler / social media CTAs
            if self._is_filler(sentence):
                continue

            # This looks like a factual claim — classify it
            claim_type = self._classify_claim_type(sentence)
            risk_level = self._assign_risk_level(claim_type)
            entities = self._extract_entities(sentence)
            time_sensitivity = self._assess_time_sensitivity(sentence)

            claim_counter += 1
            claims.append(Claim(
                claim_id=f"C{claim_counter}",
                claim_text=sentence,
                claim_type=claim_type,
                entities=entities,
                risk_level=risk_level,
                time_sensitivity=time_sensitivity,
                needs_evidence=True,
            ))

        logger.info("Rule-based extraction: %d claims from %d sentences", len(claims), len(sentences))
        return claims

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Handle numbered lists at line start (e.g., "1. item") — only 1-3 digit markers
        text = re.sub(r"(?m)^\s*(\d{1,3})\.\s+", r"\1) ", text)

        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\(])", text)

        # Also split on newlines that look like separate statements
        expanded: list[str] = []
        for s in sentences:
            parts = s.split("\n")
            for p in parts:
                p = p.strip()
                if p:
                    # Remove list markers
                    p = re.sub(r"^[\d]+\)\s*", "", p)
                    p = re.sub(r"^[-*•]\s*", "", p)
                    expanded.append(p)

        return expanded

    def _is_opinion(self, sentence: str) -> bool:
        """Check if a sentence is an opinion rather than a factual claim."""
        lower = sentence.lower()
        for pattern in _OPINION_INDICATORS:
            if re.search(pattern, lower):
                return True
        return False

    def _is_filler(self, sentence: str) -> bool:
        """Check if a sentence is filler, CTA, or social media noise."""
        lower = sentence.lower().strip()
        for pattern in _FILTER_PATTERNS:
            if re.search(pattern, lower):
                return True
        return False

    def _classify_claim_type(self, sentence: str) -> ClaimType:
        """Classify a claim by type based on keyword matching."""
        lower = sentence.lower()
        words = set(re.findall(r"\b\w+\b", lower))

        # Score each type
        scores = {
            ClaimType.MEDICAL: len(words & _MEDICAL_KEYWORDS),
            ClaimType.FINANCIAL: len(words & _FINANCIAL_KEYWORDS),
            ClaimType.POLITICAL: len(words & _POLITICAL_KEYWORDS),
            ClaimType.SCIENCE: len(words & _SCIENCE_KEYWORDS),
        }

        # Check for statistics / numbers
        has_numbers = bool(re.search(r"\b\d+[\d.,]*%?\b", sentence))
        has_stats_words = bool(re.search(r"\b(percent|percentage|ratio|average|median|total|rose|fell|increased|decreased)\b", lower))
        if has_numbers and has_stats_words:
            scores[ClaimType.STATISTICS] = max(scores.values()) + 1 if scores else 1

        # Return the highest-scoring type, or GENERAL if no matches
        if max(scores.values(), default=0) > 0:
            return max(scores, key=scores.get)  # type: ignore[arg-type]

        return ClaimType.GENERAL

    def _assign_risk_level(self, claim_type: ClaimType) -> RiskLevel:
        """Assign risk level based on claim type."""
        high_risk = {ClaimType.MEDICAL, ClaimType.FINANCIAL, ClaimType.POLITICAL}
        if claim_type in high_risk:
            return RiskLevel.HIGH
        elif claim_type == ClaimType.SCIENCE:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _extract_entities(self, sentence: str) -> list[str]:
        """Extract key entities from a sentence (simplified NER)."""
        entities: list[str] = []

        # Capitalized words/phrases (potential proper nouns)
        proper_nouns = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", sentence)
        # Filter out sentence starters (naive: skip first word)
        words = sentence.split()
        first_word = words[0] if words else ""
        for noun in proper_nouns:
            if noun != first_word and noun not in {"The", "This", "That", "These", "Those", "Some", "Many", "No"}:
                entities.append(noun)

        # Numbers with context (e.g., "40%", "$3,499", "4.5 billion")
        numbers = re.findall(r"\$?[\d,]+\.?\d*\s*(?:billion|million|thousand|%|percent)?", sentence)
        entities.extend([n.strip() for n in numbers if n.strip()])

        # Dates
        dates = re.findall(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}\b",
            sentence,
        )
        entities.extend(dates)

        # Year references
        years = re.findall(r"\b(19|20)\d{2}\b", sentence)
        entities.extend(years)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for e in entities:
            if e.lower() not in seen:
                seen.add(e.lower())
                unique.append(e)

        return unique[:8]  # Limit to 8 entities

    def _assess_time_sensitivity(self, sentence: str) -> str:
        """Assess how time-sensitive a claim is."""
        lower = sentence.lower()

        # High: specific dates, "today", "this week", "just"
        if re.search(r"\b(today|yesterday|this week|this month|just|breaking|latest)\b", lower):
            return "high"

        # Medium: year references, "recently", "last year"
        if re.search(r"\b(20\d{2}|recently|last year|last month|current)\b", lower):
            return "medium"

        return "low"

    # -------------------------------------------------------------------
    # Gemini LLM extraction (optional enhancement)
    # -------------------------------------------------------------------

    def _extract_with_gemini(self, text: str) -> list[Claim]:
        """
        Extract claims using Google Gemini LLM.

        Sends the text to Gemini with a structured prompt and parses
        the JSON response into Claim objects.

        Only called when GOOGLE_API_KEY is available.
        """
        import json

        prompt = f"""You are a claim extraction agent. Analyze the following text and extract all factual, verifiable claims.

RULES:
- Extract ONLY factual claims that can be verified with evidence.
- IGNORE opinions, emotions, jokes, vague predictions, insults, marketing hype, personal preferences, and questions.
- For each claim, classify it as one of: medical, financial, political, science, general, statistics.
- Assign a risk_level: high (medical/financial/political), medium (science), low (general).
- Extract key entities mentioned in the claim.

OUTPUT FORMAT (strict JSON):
{{
  "claims": [
    {{
      "claim_text": "exact claim text",
      "claim_type": "medical",
      "entities": ["entity1", "entity2"],
      "risk_level": "high",
      "time_sensitivity": "medium"
    }}
  ]
}}

TEXT TO ANALYZE:
{text}

Return ONLY the JSON, no other text."""

        response = self._gemini_model.generate_content(prompt)
        response_text = response.text.strip()

        # Parse JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        data = json.loads(response_text)
        claims_data = data.get("claims", [])

        claims: list[Claim] = []
        for i, item in enumerate(claims_data, 1):
            try:
                claim_type = ClaimType(item.get("claim_type", "general"))
            except ValueError:
                claim_type = ClaimType.GENERAL

            try:
                risk = RiskLevel(item.get("risk_level", "medium"))
            except ValueError:
                risk = self._assign_risk_level(claim_type)

            claims.append(Claim(
                claim_id=f"C{i}",
                claim_text=item.get("claim_text", ""),
                claim_type=claim_type,
                entities=item.get("entities", []),
                risk_level=risk,
                time_sensitivity=item.get("time_sensitivity", "low"),
                needs_evidence=True,
            ))

        return claims
