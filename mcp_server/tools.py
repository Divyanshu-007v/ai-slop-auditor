"""
MCP Tool Implementations for the Evidence Server.

Each function is a factory that returns a tool handler. This pattern
allows tools to capture configuration (e.g., fixtures data) via closures
while maintaining a clean handler signature for the MCP server.

Tool naming and parameter conventions follow the MCP specification:
  - Tool names are snake_case identifiers
  - Parameters match the JSON Schema defined in MCPToolSchema
  - Return values are plain dicts (JSON-serializable)
"""

from __future__ import annotations

import os
import re
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Normalize text for fuzzy matching: lowercase, strip punctuation."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _keyword_match_score(query: str, target: str) -> float:
    """
    Compute a simple keyword overlap score between query and target.
    Returns a value between 0.0 and 1.0.
    """
    query_words = set(_normalize(query).split())
    target_words = set(_normalize(target).split())

    if not query_words:
        return 0.0

    overlap = query_words & target_words
    # Jaccard-like but weighted toward query coverage
    return len(overlap) / len(query_words)


# ---------------------------------------------------------------------------
# Tool: retrieve_local_evidence
# ---------------------------------------------------------------------------

def make_retrieve_local_evidence(fixtures: dict[str, list[dict]]) -> Callable:
    """
    Factory for the retrieve_local_evidence tool.

    MCP Tool Schema:
        name: retrieve_local_evidence
        description: Search local evidence fixtures for matching evidence.
        parameters:
            query (str, required): Search query text
            claim_type (str, optional): Claim category for filtering

    This tool performs fuzzy keyword matching against the fixture claim keys
    and returns matching evidence entries ranked by relevance.
    """

    def retrieve_local_evidence(query: str, claim_type: str = "") -> list[dict]:
        """Search local fixtures for evidence matching the query."""
        results = []

        for claim_key, evidence_list in fixtures.items():
            score = _keyword_match_score(query, claim_key)

            # Accept matches above a threshold
            if score >= 0.3:
                for evidence in evidence_list:
                    entry = dict(evidence)
                    entry["match_score"] = round(score, 3)
                    entry["matched_claim_key"] = claim_key
                    results.append(entry)

        # Sort by match score (descending), then credibility
        results.sort(
            key=lambda e: (e.get("match_score", 0), e.get("credibility_score", 0)),
            reverse=True,
        )

        logger.info(
            "retrieve_local_evidence: query='%s', found %d results",
            query[:60],
            len(results),
        )

        return results

    return retrieve_local_evidence


# ---------------------------------------------------------------------------
# Tool: search_news
# ---------------------------------------------------------------------------

def make_search_news() -> Callable:
    """
    Factory for the search_news tool.

    MCP Tool Schema:
        name: search_news
        description: Search recent news for evidence. Uses live API if configured.
        parameters:
            query (str, required): Search query
            date_range (str, optional): Date range filter

    If NEWS_API_KEY is set in the environment, this could be extended to
    call a live news API. For MVP, returns an informational stub.
    """

    def search_news(query: str, date_range: str = "") -> list[dict]:
        """Search news sources for evidence (stub/optional live)."""
        api_key = os.environ.get("NEWS_API_KEY", "")

        if api_key:
            # TODO: Implement live news API call using NEWS_API_KEY
            logger.info("NEWS_API_KEY detected but live search not implemented in MVP")

        return [{
            "source_title": "News Search (Not Configured)",
            "source_type": "stub",
            "snippet": f"Live news search is not configured in MVP mode. "
                       f"Query: '{query}'. Set NEWS_API_KEY in .env to enable.",
            "credibility_score": 0,
            "relevance_score": 0,
            "supports_claim": False,
            "contradicts_claim": False,
            "is_stub": True,
        }]

    return search_news


# ---------------------------------------------------------------------------
# Tool: search_factcheck
# ---------------------------------------------------------------------------

def make_search_factcheck() -> Callable:
    """
    Factory for the search_factcheck tool.

    MCP Tool Schema:
        name: search_factcheck
        description: Search fact-checking databases.
        parameters:
            query (str, required): Claim text to fact-check

    Stub implementation for MVP. Could be extended to use Google Fact Check
    API or ClaimBuster API.
    """

    def search_factcheck(query: str) -> list[dict]:
        """Search fact-check databases (stub in MVP)."""
        return [{
            "source_title": "Fact-Check Search (Not Configured)",
            "source_type": "stub",
            "snippet": f"Live fact-check search is not configured in MVP mode. "
                       f"Query: '{query}'. A future version could use Google Fact Check API.",
            "credibility_score": 0,
            "relevance_score": 0,
            "supports_claim": False,
            "contradicts_claim": False,
            "is_stub": True,
        }]

    return search_factcheck


# ---------------------------------------------------------------------------
# Tool: search_pubmed
# ---------------------------------------------------------------------------

def make_search_pubmed() -> Callable:
    """
    Factory for the search_pubmed tool.

    MCP Tool Schema:
        name: search_pubmed
        description: Search PubMed for medical/scientific evidence.
        parameters:
            query (str, required): Medical/scientific search query

    Stub implementation for MVP. Could be extended to use NCBI E-utilities API.
    """

    def search_pubmed(query: str) -> list[dict]:
        """Search PubMed for evidence (stub in MVP)."""
        return [{
            "source_title": "PubMed Search (Not Configured)",
            "source_type": "stub",
            "snippet": f"Live PubMed search is not configured in MVP mode. "
                       f"Query: '{query}'. A future version could use NCBI E-utilities.",
            "credibility_score": 0,
            "relevance_score": 0,
            "supports_claim": False,
            "contradicts_claim": False,
            "is_stub": True,
        }]

    return search_pubmed


# ---------------------------------------------------------------------------
# Tool: fetch_url_text
# ---------------------------------------------------------------------------

def make_fetch_url_text() -> Callable:
    """
    Factory for the fetch_url_text tool.

    MCP Tool Schema:
        name: fetch_url_text
        description: Fetch text content from a URL.
        parameters:
            url (str, required): URL to fetch

    Stub implementation for MVP. Does not make real HTTP requests.
    """

    def fetch_url_text(url: str) -> dict:
        """Fetch URL text content (stub in MVP)."""
        return {
            "url": url,
            "text": "Live URL fetching is not available in MVP mode.",
            "is_stub": True,
        }

    return fetch_url_text


# ---------------------------------------------------------------------------
# Tool: rank_sources
# ---------------------------------------------------------------------------

def make_rank_sources(credibility_data: dict[str, dict]) -> Callable:
    """
    Factory for the rank_sources tool.

    MCP Tool Schema:
        name: rank_sources
        description: Rank evidence items by credibility and relevance.
        parameters:
            evidence_list (list[dict], required): Evidence items to rank

    Uses the source_credibility.json data to look up credibility scores
    by source type, then computes a weighted ranking score.
    """

    def rank_sources(evidence_list: list[dict]) -> list[dict]:
        """Rank evidence by credibility × relevance score."""
        from mcp_server.source_ranker import rank_evidence
        return rank_evidence(evidence_list, credibility_data)

    return rank_sources
