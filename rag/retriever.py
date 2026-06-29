"""
Evidence Retriever — RAG-style evidence retrieval pipeline.

Wraps the MCP Evidence Server to provide a clean interface for agents.
Handles query generation, tool selection, and result aggregation.
"""

from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

from models import Claim, ClaimType, Evidence

if TYPE_CHECKING:
    from mcp_server.server import MCPEvidenceServer

logger = logging.getLogger(__name__)


# Common English stop words to filter from queries
_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "and", "but", "or",
    "not", "no", "nor", "so", "yet", "both", "each", "few", "more",
    "most", "other", "some", "such", "than", "too", "very", "just",
    "about", "that", "this", "these", "those", "it", "its", "i", "me",
    "my", "we", "our", "you", "your", "he", "she", "they", "them",
}


class EvidenceRetriever:
    """
    RAG-style evidence retrieval pipeline.

    Orchestrates:
      1. Query generation from a claim
      2. MCP tool selection based on claim type
      3. Evidence retrieval via MCP server
      4. Ranking and deduplication of results
    """

    def __init__(self, mcp_server: MCPEvidenceServer):
        """
        Args:
            mcp_server: An initialized MCPEvidenceServer instance.
        """
        self._server = mcp_server

    def retrieve_for_claim(self, claim: Claim) -> list[Evidence]:
        """
        Retrieve evidence for a given claim.

        Generates search queries, selects appropriate MCP tools,
        retrieves evidence, ranks results, and returns Evidence objects.

        Args:
            claim: The Claim to find evidence for.

        Returns:
            List of Evidence objects, ranked by relevance/credibility.
        """
        # Step 1: Generate search queries
        queries = self._generate_queries(claim)
        logger.info("Generated %d queries for claim '%s'", len(queries), claim.claim_text[:50])

        # Step 2: Select MCP tools based on claim type
        tool_names = self._select_tools(claim.claim_type)
        logger.info("Selected tools: %s", tool_names)

        # Step 3: Call MCP tools and collect raw evidence
        raw_evidence: list[dict] = []

        for query in queries:
            for tool_name in tool_names:
                try:
                    # Build tool-specific arguments — only retrieve_local_evidence accepts claim_type
                    tool_args: dict = {"query": query}
                    if tool_name == "retrieve_local_evidence":
                        tool_args["claim_type"] = claim.claim_type.value
                    result = self._server.call_tool(tool_name, tool_args)
                    if result.get("status") == "success":
                        tool_results = result.get("result", [])
                        if isinstance(tool_results, list):
                            raw_evidence.extend(tool_results)
                        elif isinstance(tool_results, dict):
                            raw_evidence.append(tool_results)
                except Exception as e:
                    logger.warning("Tool %s failed for query '%s': %s", tool_name, query[:40], e)

        # Step 4: Rank via MCP rank_sources tool
        if raw_evidence:
            rank_result = self._server.call_tool("rank_sources", {"evidence_list": raw_evidence})
            if rank_result.get("status") == "success":
                raw_evidence = rank_result.get("result", raw_evidence)

        # Step 5: Convert to Evidence models
        evidence_list: list[Evidence] = []
        for item in raw_evidence:
            if item.get("is_stub"):
                continue
            try:
                evidence_list.append(Evidence(
                    source_title=item.get("source_title", "Unknown"),
                    source_type=item.get("source_type", "unknown"),
                    source_url=item.get("source_url", ""),
                    snippet=item.get("snippet", ""),
                    published_date=item.get("published_date", ""),
                    credibility_score=float(item.get("credibility_score", 50)),
                    relevance_score=float(item.get("relevance_score", 50)),
                    supports_claim=bool(item.get("supports_claim", False)),
                    contradicts_claim=bool(item.get("contradicts_claim", False)),
                ))
            except Exception as e:
                logger.warning("Failed to parse evidence item: %s", e)

        logger.info("Retrieved %d evidence items for claim '%s'", len(evidence_list), claim.claim_text[:50])
        return evidence_list

    def _generate_queries(self, claim: Claim) -> list[str]:
        """
        Generate 2-3 search queries from a claim.

        Strategy:
          1. Use the raw claim text (cleaned)
          2. Extract keywords and form a keyword-only query
          3. Add claim type context for domain-specific search
        """
        queries = []

        # Query 1: Cleaned claim text
        clean_text = re.sub(r"[^\w\s]", " ", claim.claim_text).strip()
        clean_text = re.sub(r"\s+", " ", clean_text)
        queries.append(clean_text.lower())

        # Query 2: Keywords only (stop words removed)
        words = clean_text.lower().split()
        keywords = [w for w in words if w not in _STOP_WORDS and len(w) > 2]
        if keywords:
            queries.append(" ".join(keywords))

        # Query 3: Claim type + key terms
        if claim.entities:
            entity_query = f"{claim.claim_type.value} {' '.join(claim.entities[:3])}"
            queries.append(entity_query)
        elif keywords:
            type_query = f"{claim.claim_type.value} {' '.join(keywords[:4])}"
            queries.append(type_query)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_queries: list[str] = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        return unique_queries[:3]

    def _select_tools(self, claim_type: ClaimType) -> list[str]:
        """
        Select MCP tools based on claim type.

        Always includes retrieve_local_evidence.
        Adds domain-specific tools for specialized claim types.
        """
        tools = ["retrieve_local_evidence"]

        type_tools = {
            ClaimType.MEDICAL: ["search_pubmed"],
            ClaimType.FINANCIAL: ["search_news"],
            ClaimType.POLITICAL: ["search_factcheck", "search_news"],
            ClaimType.SCIENCE: ["search_pubmed"],
        }

        extra = type_tools.get(claim_type, [])
        tools.extend(extra)

        return tools
