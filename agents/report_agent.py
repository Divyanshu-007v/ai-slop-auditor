"""
Report Agent — generates final audit reports.

Agent Role: Aggregate all verdicts into a comprehensive audit report
            with summary statistics, claim-by-claim details, and
            export-ready Markdown/JSON formats.
Agent Skill: report_gen
Input: list[Verdict] + session_id
Output: AuditReport

Demonstrates: Agent Skills, structured output generation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from models import AuditReport, Verdict, VerdictLabel

logger = logging.getLogger(__name__)


class ReportAgent:
    """
    Agent Role: Generate final audit reports.
    Agent Skill: report_gen
    Input: list[Verdict] + session_id
    Output: AuditReport
    """

    name: str = "report_agent"
    description: str = "Generates comprehensive audit reports"

    def generate_report(
        self,
        verdicts: list[Verdict],
        session_id: str,
        input_text: str = "",
        extraction_mode: str = "rule-based",
    ) -> AuditReport:
        """
        Generate a complete audit report from verdicts.

        Args:
            verdicts: List of all verdicts for the session.
            session_id: Session identifier.
            input_text: Original input text (for preview).
            extraction_mode: 'rule-based' or 'gemini-llm'.

        Returns:
            AuditReport with summary stats, Markdown report, and all verdicts.
        """
        # Compute summary statistics
        total = len(verdicts)
        supported = sum(1 for v in verdicts if v.verdict == VerdictLabel.SUPPORTED)
        mostly = sum(1 for v in verdicts if v.verdict == VerdictLabel.MOSTLY_SUPPORTED)
        partially = sum(1 for v in verdicts if v.verdict == VerdictLabel.PARTIALLY_SUPPORTED)
        unsupported = sum(1 for v in verdicts if v.verdict == VerdictLabel.UNSUPPORTED)
        contradicted = sum(1 for v in verdicts if v.verdict == VerdictLabel.CONTRADICTED)
        insufficient = sum(1 for v in verdicts if v.verdict == VerdictLabel.INSUFFICIENT_EVIDENCE)
        human_review = sum(1 for v in verdicts if v.human_review_required)

        # Generate Markdown report
        markdown = self._generate_markdown(
            verdicts, total, supported, mostly, partially,
            unsupported, contradicted, insufficient, human_review,
            extraction_mode,
        )

        # Generate risk summary
        risk_summary = self._generate_risk_summary(verdicts, total, human_review)

        report = AuditReport(
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            input_text_preview=input_text[:200] if input_text else "",
            total_claims=total,
            supported_claims=supported,
            mostly_supported_claims=mostly,
            partially_supported_claims=partially,
            unsupported_claims=unsupported,
            contradicted_claims=contradicted,
            insufficient_evidence_claims=insufficient,
            human_review_claims=human_review,
            verdicts=verdicts,
            markdown_report=markdown,
            risk_summary=risk_summary,
            extraction_mode=extraction_mode,
        )

        logger.info(
            "Generated report for session %s: %d claims, %d flagged",
            session_id, total, human_review,
        )

        return report

    def _generate_markdown(
        self,
        verdicts: list[Verdict],
        total: int,
        supported: int,
        mostly: int,
        partially: int,
        unsupported: int,
        contradicted: int,
        insufficient: int,
        human_review: int,
        extraction_mode: str,
    ) -> str:
        """Generate a Markdown-formatted audit report."""
        lines: list[str] = []

        # Header
        lines.append("# 🔍 AI-Slop & Misinformation Audit Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Extraction Mode:** {extraction_mode}")
        lines.append("")

        # Summary
        lines.append("## 📊 Summary")
        lines.append("")
        lines.append(f"| Metric | Count |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Claims | {total} |")
        lines.append(f"| ✅ Supported | {supported} |")
        lines.append(f"| 🟡 Mostly Supported | {mostly} |")
        lines.append(f"| 🟠 Partially Supported | {partially} |")
        lines.append(f"| ❌ Unsupported | {unsupported} |")
        lines.append(f"| 🔴 Contradicted | {contradicted} |")
        lines.append(f"| ⬜ Insufficient Evidence | {insufficient} |")
        lines.append(f"| ⚠️ Flagged for Human Review | {human_review} |")
        lines.append("")

        # Claim-by-claim details
        lines.append("## 📋 Claim-by-Claim Analysis")
        lines.append("")

        for v in verdicts:
            emoji = self._verdict_emoji(v.verdict)
            review_flag = " ⚠️ **HUMAN REVIEW REQUIRED**" if v.human_review_required else ""
            lines.append(f"### {v.claim_id}: {emoji} {v.verdict.value}{review_flag}")
            lines.append("")
            lines.append(f"**Claim:** {v.claim_text}")
            lines.append(f"**Trust Score:** {v.trust_score}/100")
            lines.append("")

            # Evidence summary
            if v.evidence_used:
                lines.append(f"**Evidence ({len(v.evidence_used)} sources):**")
                for e in v.evidence_used[:3]:  # Show top 3
                    support_indicator = "✅" if e.supports_claim else ("❌" if e.contradicts_claim else "➖")
                    lines.append(f"- {support_indicator} {e.source_title}: {e.snippet[:150]}...")
                lines.append("")
            else:
                lines.append("**Evidence:** None found")
                lines.append("")

            # Citations
            if v.citations:
                lines.append("**Citations:**")
                for cite in v.citations:
                    lines.append(f"- {cite}")
                lines.append("")

            # Risk notes
            if v.risk_notes:
                lines.append("**Risk Notes:**")
                for note in v.risk_notes:
                    lines.append(f"- {note}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # Human review section
        flagged = [v for v in verdicts if v.human_review_required]
        if flagged:
            lines.append("## ⚠️ Claims Requiring Human Review")
            lines.append("")
            for v in flagged:
                lines.append(f"- **{v.claim_id}**: {v.claim_text} (Score: {v.trust_score}/100)")
            lines.append("")

        # Limitations
        lines.append("## ⚖️ Limitations")
        lines.append("")
        lines.append("- This system is an auditing assistant, not a final authority.")
        lines.append("- Results should be verified by domain experts.")
        lines.append("- The system does not provide medical, legal, or financial advice.")
        lines.append("- Evidence is limited to available sources (local fixtures in MVP mode).")
        lines.append("- Rule-based extraction may miss some claims or include non-claims.")
        lines.append("")

        return "\n".join(lines)

    def _generate_risk_summary(
        self, verdicts: list[Verdict], total: int, human_review: int,
    ) -> str:
        """Generate a brief risk summary."""
        if total == 0:
            return "No claims to assess."

        review_pct = (human_review / total * 100) if total else 0

        contradicted = sum(1 for v in verdicts if v.verdict == VerdictLabel.CONTRADICTED)
        unsupported = sum(1 for v in verdicts if v.verdict == VerdictLabel.UNSUPPORTED)

        if contradicted > total * 0.5:
            level = "🔴 HIGH RISK"
            detail = "More than half of the claims are contradicted by evidence."
        elif unsupported + contradicted > total * 0.3:
            level = "🟠 MODERATE-HIGH RISK"
            detail = "A significant portion of claims lack support or are contradicted."
        elif human_review > total * 0.5:
            level = "🟡 MODERATE RISK"
            detail = "Many claims require human review for full verification."
        else:
            level = "🟢 LOW-MODERATE RISK"
            detail = "Most claims are supported or partially supported by evidence."

        return f"{level}: {detail} ({human_review}/{total} claims flagged, {review_pct:.0f}% review rate)"

    @staticmethod
    def _verdict_emoji(verdict: VerdictLabel) -> str:
        """Get emoji for a verdict label."""
        mapping = {
            VerdictLabel.SUPPORTED: "✅",
            VerdictLabel.MOSTLY_SUPPORTED: "🟡",
            VerdictLabel.PARTIALLY_SUPPORTED: "🟠",
            VerdictLabel.UNSUPPORTED: "❌",
            VerdictLabel.CONTRADICTED: "🔴",
            VerdictLabel.INSUFFICIENT_EVIDENCE: "⬜",
            VerdictLabel.NEEDS_HUMAN_REVIEW: "⚠️",
        }
        return mapping.get(verdict, "❓")

    def to_json(self, report: AuditReport) -> str:
        """Export the audit report as a JSON string."""
        return json.dumps(report.model_dump(), indent=2, default=str)
