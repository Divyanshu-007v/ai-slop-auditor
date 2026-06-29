"""
Summary Tree — hierarchical evidence summarization.

Merges multiple evidence snippets for a single claim into a concise
evidence summary. Used by the Consensus Agent to compare claim vs
aggregated evidence without getting lost in individual snippets.
"""

from __future__ import annotations

from models import Evidence


class SummaryTree:
    """
    Hierarchical summarization of evidence snippets.

    For MVP, this performs extractive summarization:
      - Groups evidence by support/contradict
      - Selects the most relevant snippet from each group
      - Produces a structured summary
    """

    def summarize(self, evidence_list: list[Evidence]) -> dict:
        """
        Summarize a list of evidence into a structured summary.

        Args:
            evidence_list: Evidence objects to summarize.

        Returns:
            Dict with keys:
              - supporting_summary: str
              - contradicting_summary: str
              - neutral_summary: str
              - source_count: int
              - agreement_ratio: float (0-1, proportion supporting)
        """
        if not evidence_list:
            return {
                "supporting_summary": "",
                "contradicting_summary": "",
                "neutral_summary": "",
                "source_count": 0,
                "agreement_ratio": 0.0,
            }

        supporting: list[Evidence] = []
        contradicting: list[Evidence] = []
        neutral: list[Evidence] = []

        for ev in evidence_list:
            if ev.supports_claim:
                supporting.append(ev)
            elif ev.contradicts_claim:
                contradicting.append(ev)
            else:
                neutral.append(ev)

        total = len(evidence_list)
        agreement_ratio = len(supporting) / total if total > 0 else 0.0

        return {
            "supporting_summary": self._merge_snippets(supporting),
            "contradicting_summary": self._merge_snippets(contradicting),
            "neutral_summary": self._merge_snippets(neutral),
            "source_count": total,
            "agreement_ratio": round(agreement_ratio, 3),
        }

    def _merge_snippets(self, evidence: list[Evidence]) -> str:
        """
        Merge evidence snippets into a single summary string.

        For MVP: Concatenates the top-2 most relevant snippets
        (by relevance_score) with source attribution.
        """
        if not evidence:
            return ""

        # Sort by relevance score descending
        sorted_ev = sorted(evidence, key=lambda e: e.relevance_score, reverse=True)

        # Take top 2 snippets
        parts: list[str] = []
        for ev in sorted_ev[:2]:
            attribution = f"[{ev.source_title}]"
            # Truncate very long snippets
            snippet = ev.snippet[:300] + "..." if len(ev.snippet) > 300 else ev.snippet
            parts.append(f"{attribution}: {snippet}")

        return " | ".join(parts)
