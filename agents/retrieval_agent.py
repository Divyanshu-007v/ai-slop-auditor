"""
Deep Retrieval Agent — retrieves evidence for claims via MCP tools.

Agent Role: Turn each claim into search queries and retrieve evidence
            using MCP-style tools.
Agent Skill: evidence_fetch
Input: Claim object
Output: list[Evidence]

Demonstrates: MCP tool integration, RAG-style retrieval.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from models import Claim, Evidence
from rag.retriever import EvidenceRetriever

if TYPE_CHECKING:
    from mcp_server.server import MCPEvidenceServer

logger = logging.getLogger(__name__)


class RetrievalAgent:
    """
    Agent Role: Retrieve evidence for factual claims via MCP tools.
    Agent Skill: evidence_fetch
    Input: Claim
    Output: list[Evidence]

    Responsibilities:
      - Generate search queries from claim text
      - Select appropriate evidence sources based on claim type
      - Call MCP tools to retrieve evidence
      - Rank and return evidence list
    """

    name: str = "retrieval_agent"
    description: str = "Retrieves evidence for claims using MCP tools"

    def __init__(self, mcp_server: MCPEvidenceServer):
        """
        Args:
            mcp_server: Initialized MCP Evidence Server instance.
        """
        self._retriever = EvidenceRetriever(mcp_server)
        self._server = mcp_server

    def retrieve_evidence(self, claim: Claim) -> list[Evidence]:
        """
        Retrieve evidence for a given claim.

        Delegates to the EvidenceRetriever which handles query generation,
        tool selection, MCP calls, and ranking.

        Args:
            claim: The Claim to find evidence for.

        Returns:
            List of Evidence objects, ranked by relevance/credibility.
            Returns empty list if no evidence found.
        """
        try:
            evidence = self._retriever.retrieve_for_claim(claim)
            logger.info(
                "Retrieved %d evidence items for claim '%s' [type=%s]",
                len(evidence),
                claim.claim_text[:50],
                claim.claim_type.value,
            )
            return evidence
        except Exception as e:
            logger.error("Evidence retrieval failed for claim '%s': %s", claim.claim_text[:50], e)
            return []

    def get_available_tools(self) -> list[dict]:
        """List all available MCP tools."""
        return self._server.list_tools()
