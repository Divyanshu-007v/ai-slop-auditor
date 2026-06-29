"""
Source Ranker — ranks evidence items by credibility and relevance.

Used by the rank_sources MCP tool and internally by the Retrieval Agent
to order evidence from most trustworthy to least trustworthy.

Ranking formula:
    ranking_score = credibility_score * 0.6 + relevance_score * 0.4
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def rank_evidence(
    evidence_list: list[dict[str, Any]],
    credibility_data: dict[str, dict] | None = None,
) -> list[dict[str, Any]]:
    """
    Rank a list of evidence items by credibility and relevance.

    For each evidence item:
      1. Look up the credibility score from credibility_data by source_type.
         If the source_type is not found, use the item's own credibility_score
         or default to 50.
      2. Compute: ranking_score = credibility * 0.6 + relevance * 0.4
      3. Sort descending by ranking_score.
      4. Deduplicate by source_url (keep highest-ranked version).

    Args:
        evidence_list: List of evidence dicts with at minimum
                       'credibility_score' and 'relevance_score'.
        credibility_data: Optional dict mapping source_type -> {credibility_score: int}.

    Returns:
        Sorted, deduplicated list of evidence dicts with 'ranking_score' added.
    """
    credibility_data = credibility_data or {}
    scored = []

    for item in evidence_list:
        # Skip stub results
        if item.get("is_stub"):
            continue

        # Look up credibility from credibility_data by source_type
        source_type = item.get("source_type", "unknown")
        if source_type in credibility_data:
            cred_score = credibility_data[source_type].get(
                "credibility_score", item.get("credibility_score", 50)
            )
        else:
            cred_score = item.get("credibility_score", 50)

        rel_score = item.get("relevance_score", 50)

        ranking_score = cred_score * 0.6 + rel_score * 0.4

        entry = dict(item)
        entry["credibility_score"] = cred_score
        entry["ranking_score"] = round(ranking_score, 2)
        scored.append(entry)

    # Sort by ranking score descending
    scored.sort(key=lambda e: e["ranking_score"], reverse=True)

    # Deduplicate by source_url (keep first = highest ranked)
    seen_urls: set[str] = set()
    deduplicated: list[dict[str, Any]] = []

    for item in scored:
        url = item.get("source_url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        deduplicated.append(item)

    logger.info(
        "Ranked %d evidence items (%d after dedup)",
        len(scored),
        len(deduplicated),
    )

    return deduplicated
