"""
Orchestrator Agent — controls the full audit pipeline.

Agent Role: Accept user input, coordinate all agents in sequence,
            manage session memory, and return the final audit report.
Agent Skill: orchestrate
Input: Raw text + optional session_id
Output: AuditReport

Demonstrates: ADK-style multi-agent orchestration.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from models import AuditReport, Claim, Evidence, Verdict
from agents.extraction_agent import ExtractionAgent
from agents.retrieval_agent import RetrievalAgent
from agents.consensus_agent import ConsensusAgent
from agents.guardrail_agent import GuardrailAgent
from agents.report_agent import ReportAgent
from mcp_server.server import MCPEvidenceServer
from memory.session_memory import SessionMemory

logger = logging.getLogger(__name__)


# Type alias for progress callback
ProgressCallback = Callable[[str, str], None]


class OrchestratorAgent:
    """
    Agent Role: Control the full claim auditing pipeline.
    Agent Skill: orchestrate
    Input: Raw text (str)
    Output: AuditReport

    Pipeline:
      1. Create session in memory
      2. Extract claims (Extraction Agent)
      3. Retrieve evidence for each claim (Retrieval Agent)
      4. Adjudicate each claim (Consensus Agent)
      5. Apply guardrails (Guardrail Agent)
      6. Store results in memory
      7. Generate report (Report Agent)
      8. Return final AuditReport
    """

    name: str = "orchestrator_agent"
    description: str = "Orchestrates the full claim audit pipeline"

    def __init__(
        self,
        mcp_server: MCPEvidenceServer | None = None,
        session_memory: SessionMemory | None = None,
    ):
        """
        Initialize the orchestrator with all sub-agents.

        Args:
            mcp_server: Optional pre-configured MCP server.
                        If None, creates a default one.
            session_memory: Optional pre-configured session memory.
                            If None, creates a default one.
        """
        self._mcp_server = mcp_server or MCPEvidenceServer()
        self._memory = session_memory or SessionMemory()

        # Initialize all sub-agents
        self._extraction = ExtractionAgent()
        self._retrieval = RetrievalAgent(self._mcp_server)
        self._consensus = ConsensusAgent()
        self._guardrail = GuardrailAgent()
        self._report = ReportAgent()

        logger.info("OrchestratorAgent initialized with all sub-agents")

    @property
    def extraction_mode(self) -> str:
        """Current extraction mode (rule-based or gemini-llm)."""
        return self._extraction.extraction_mode

    @property
    def session_memory(self) -> SessionMemory:
        """Access the session memory."""
        return self._memory

    def run_audit(
        self,
        text: str,
        session_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> AuditReport:
        """
        Run the full audit pipeline on input text.

        Args:
            text: Input text to audit (article, transcript, social post).
            session_id: Optional existing session ID. If None, creates new.
            progress_callback: Optional callback for progress updates.
                               Called as progress_callback(stage, detail).

        Returns:
            Complete AuditReport with all verdicts, scores, and report text.
        """
        def _progress(stage: str, detail: str = "") -> None:
            """Send progress update if callback is set."""
            if progress_callback:
                progress_callback(stage, detail)
            logger.info("[%s] %s", stage, detail)

        # Step 1: Create session
        _progress("session", "Creating audit session...")
        if session_id is None:
            session_id = self._memory.create_session(
                text, extraction_mode=self._extraction.extraction_mode
            )
        _progress("session", f"Session {session_id} created")

        # Step 2: Extract claims
        _progress("extraction", "Extracting factual claims...")
        claims = self._extraction.extract_claims(text)
        _progress("extraction", f"Extracted {len(claims)} claims")

        if not claims:
            _progress("complete", "No factual claims found in input text")
            report = self._report.generate_report(
                verdicts=[],
                session_id=session_id,
                input_text=text,
                extraction_mode=self._extraction.extraction_mode,
            )
            self._memory.complete_session(session_id, 0)
            return report

        # Step 3-5: Process each claim
        all_verdicts: list[Verdict] = []

        for i, claim in enumerate(claims, 1):
            _progress("retrieval", f"Retrieving evidence for claim {i}/{len(claims)}: {claim.claim_text[:50]}...")

            # Step 3: Retrieve evidence
            evidence = self._retrieval.retrieve_evidence(claim)
            _progress("retrieval", f"Found {len(evidence)} evidence items for claim {i}")

            # Step 4: Adjudicate
            _progress("consensus", f"Adjudicating claim {i}/{len(claims)}...")
            verdict = self._consensus.adjudicate(claim, evidence)

            # Step 5: Apply guardrails
            _progress("guardrails", f"Applying guardrails to claim {i}/{len(claims)}...")
            verdict = self._guardrail.apply_guardrails(verdict, claim)

            # Store in memory
            self._memory.store_claim_result(
                session_id=session_id,
                claim_id=claim.claim_id,
                claim=claim,
                evidence=evidence,
                verdict=verdict,
            )

            all_verdicts.append(verdict)

        # Step 6: Generate report
        _progress("report", "Generating audit report...")
        report = self._report.generate_report(
            verdicts=all_verdicts,
            session_id=session_id,
            input_text=text,
            extraction_mode=self._extraction.extraction_mode,
        )

        # Mark session as complete
        self._memory.complete_session(session_id, len(claims))
        _progress("complete", f"Audit complete: {len(claims)} claims analyzed")

        return report
