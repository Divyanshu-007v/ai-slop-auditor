"""
AI-Slop & Misinformation Auditor — Streamlit UI

Main application entry point. Run with:
    streamlit run app.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv()

from agents.orchestrator_agent import OrchestratorAgent
from agents.report_agent import ReportAgent
from models import VerdictLabel


# ---------------------------------------------------------------------------
# Page Config & Custom CSS
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI-Slop & Misinformation Auditor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }

    /* Title styling */
    .main-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0;
    }

    /* Verdict badges */
    .verdict-supported {
        background-color: #10b981;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .verdict-mostly {
        background-color: #f59e0b;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .verdict-partial {
        background-color: #f97316;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .verdict-unsupported {
        background-color: #ef4444;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .verdict-contradicted {
        background-color: #dc2626;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .verdict-insufficient {
        background-color: #6b7280;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .verdict-review {
        background-color: #8b5cf6;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }

    /* Claim type badges */
    .claim-type {
        background-color: #1e3a5f;
        color: #93c5fd;
        padding: 2px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 500;
    }

    /* Risk badge */
    .risk-high {
        color: #fca5a5;
        font-weight: 600;
    }
    .risk-medium {
        color: #fcd34d;
        font-weight: 600;
    }
    .risk-low {
        color: #86efac;
        font-weight: 600;
    }

    /* Card styling */
    .claim-card {
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        background-color: #1f2937;
    }

    /* Human review alert */
    .human-review-alert {
        border-left: 4px solid #f59e0b;
        background-color: #1c1917;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
    }

    /* Trust score bar */
    .trust-score-container {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Sidebar styling */
    .sidebar-session {
        padding: 0.5rem;
        border-bottom: 1px solid #374151;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Initialize Session State
# ---------------------------------------------------------------------------

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = OrchestratorAgent()

if "report" not in st.session_state:
    st.session_state.report = None

if "processing" not in st.session_state:
    st.session_state.processing = False


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_verdict_badge(verdict: VerdictLabel) -> str:
    """Get HTML badge for a verdict label."""
    badges = {
        VerdictLabel.SUPPORTED: '<span class="verdict-supported">✅ Supported</span>',
        VerdictLabel.MOSTLY_SUPPORTED: '<span class="verdict-mostly">🟡 Mostly Supported</span>',
        VerdictLabel.PARTIALLY_SUPPORTED: '<span class="verdict-partial">🟠 Partially Supported</span>',
        VerdictLabel.UNSUPPORTED: '<span class="verdict-unsupported">❌ Unsupported</span>',
        VerdictLabel.CONTRADICTED: '<span class="verdict-contradicted">🔴 Contradicted</span>',
        VerdictLabel.INSUFFICIENT_EVIDENCE: '<span class="verdict-insufficient">⬜ Insufficient Evidence</span>',
        VerdictLabel.NEEDS_HUMAN_REVIEW: '<span class="verdict-review">⚠️ Needs Human Review</span>',
    }
    return badges.get(verdict, str(verdict.value))


def get_trust_score_color(score: float) -> str:
    """Get color for trust score visualization."""
    if score >= 90:
        return "#10b981"  # green
    elif score >= 75:
        return "#f59e0b"  # amber
    elif score >= 50:
        return "#f97316"  # orange
    elif score >= 25:
        return "#ef4444"  # red
    else:
        return "#dc2626"  # dark red


def load_sample_inputs() -> dict[str, str]:
    """Load sample input files from data/sample_inputs/."""
    samples = {}
    sample_dir = Path(__file__).parent / "data" / "sample_inputs"
    if sample_dir.exists():
        for f in sorted(sample_dir.glob("*.txt")):
            name = f.stem.replace("_", " ").title()
            samples[name] = f.read_text(encoding="utf-8")
    return samples


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🔍 About")
    st.markdown(
        "**AI-Slop & Misinformation Auditor** analyzes text for factual claims, "
        "retrieves evidence, and provides explainable trust scores."
    )

    # Extraction mode indicator
    mode = st.session_state.orchestrator.extraction_mode
    if mode == "gemini-llm":
        st.success("🟢 **Extraction Mode:** Gemini LLM")
    else:
        st.info("⚪ **Extraction Mode:** Rule-based (offline)")

    st.markdown("---")

    # Capstone concepts
    st.markdown("### 📚 Capstone Concepts")
    st.markdown("""
    1. ✅ ADK-style multi-agent architecture
    2. ✅ MCP server/tool integration
    3. ✅ Agent skills
    4. ✅ RAG-style evidence retrieval
    5. ✅ Session memory
    6. ✅ Security guardrails
    7. ✅ Human-in-the-loop review
    """)

    st.markdown("---")

    # Session history
    st.markdown("### 📁 Session History")
    try:
        sessions = st.session_state.orchestrator.session_memory.list_sessions(limit=10)
        if sessions:
            for s in sessions:
                status_icon = "✅" if s["status"] == "completed" else "⏳"
                with st.expander(f"{status_icon} {s['session_id'][:8]}... ({s['total_claims']} claims)"):
                    st.caption(f"Created: {s['created_at'][:19]}")
                    st.caption(f"Mode: {s['extraction_mode']}")
                    st.text(s["input_preview"][:100] + "...")
        else:
            st.caption("No previous sessions")
    except Exception:
        st.caption("No previous sessions")


# ---------------------------------------------------------------------------
# Main Content
# ---------------------------------------------------------------------------

# Header
st.markdown('<h1 class="main-title">🔍 AI-Slop & Misinformation Auditor</h1>', unsafe_allow_html=True)
st.markdown(
    "Paste an article, transcript, or social media post below. "
    "The system will extract factual claims, retrieve evidence, and "
    "provide explainable trust scores."
)
st.caption(
    "⚖️ *This is an auditing assistant, not a final authority. "
    "Results should be independently verified by domain experts.*"
)

st.markdown("---")

# Input Section
col_input, col_sample = st.columns([3, 1])

with col_sample:
    st.markdown("#### 📝 Sample Inputs")
    samples = load_sample_inputs()
    sample_choice = st.selectbox(
        "Load a sample:",
        options=["(none)"] + list(samples.keys()),
        label_visibility="collapsed",
    )

with col_input:
    default_text = samples.get(sample_choice, "") if sample_choice != "(none)" else ""
    user_input = st.text_area(
        "Paste text to analyze:",
        value=default_text,
        height=200,
        placeholder="Paste an article, transcript, or social media post here...",
    )

# Analyze button
col_btn, col_spacer = st.columns([1, 3])
with col_btn:
    analyze_clicked = st.button(
        "🔍 Analyze Claims",
        type="primary",
        use_container_width=True,
        disabled=not user_input.strip(),
    )


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

if analyze_clicked and user_input.strip():
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    stage_progress = {
        "session": 0.05,
        "extraction": 0.20,
        "retrieval": 0.50,
        "consensus": 0.70,
        "guardrails": 0.85,
        "report": 0.95,
        "complete": 1.0,
    }

    def update_progress(stage: str, detail: str) -> None:
        pct = stage_progress.get(stage, 0)
        progress_bar.progress(pct)
        status_text.markdown(f"**{stage.title()}:** {detail}")

    try:
        report = st.session_state.orchestrator.run_audit(
            text=user_input,
            progress_callback=update_progress,
        )
        st.session_state.report = report
        progress_bar.progress(1.0)
        status_text.markdown("**✅ Analysis complete!**")
    except Exception as e:
        st.error(f"❌ Analysis failed: {str(e)}")
        st.session_state.report = None


# ---------------------------------------------------------------------------
# Results Display
# ---------------------------------------------------------------------------

report = st.session_state.report

if report is not None:
    st.markdown("---")

    # Summary Metrics
    st.markdown("## 📊 Summary")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Claims", report.total_claims)
    m2.metric("✅ Supported", report.supported_claims + report.mostly_supported_claims)
    m3.metric("❌ Unsupported", report.unsupported_claims + report.contradicted_claims)
    m4.metric("⬜ Insufficient", report.insufficient_evidence_claims)
    m5.metric("⚠️ Human Review", report.human_review_claims)

    # Risk summary
    if report.risk_summary:
        st.markdown(f"**Risk Assessment:** {report.risk_summary}")

    st.markdown("---")

    # Extracted Claims & Verdicts
    st.markdown("## 📋 Claim-by-Claim Analysis")

    for v in report.verdicts:
        with st.expander(
            f"**{v.claim_id}** — {v.claim_text[:80]}{'...' if len(v.claim_text) > 80 else ''}",
            expanded=v.human_review_required,
        ):
            # Verdict and score row
            vcol1, vcol2, vcol3 = st.columns([2, 1, 1])

            with vcol1:
                st.markdown(get_verdict_badge(v.verdict), unsafe_allow_html=True)

            with vcol2:
                score_color = get_trust_score_color(v.trust_score)
                st.markdown(
                    f'<span style="color: {score_color}; font-weight: 700; font-size: 1.2rem;">'
                    f"Trust: {v.trust_score}/100</span>",
                    unsafe_allow_html=True,
                )

            with vcol3:
                if v.human_review_required:
                    st.markdown("⚠️ **Human Review Required**")

            # Trust score progress bar
            st.progress(v.trust_score / 100)

            # Full claim text
            st.markdown(f"**Claim:** {v.claim_text}")

            # Evidence
            if v.evidence_used:
                st.markdown(f"**Evidence ({len(v.evidence_used)} sources):**")
                for e in v.evidence_used:
                    icon = "✅" if e.supports_claim else ("❌" if e.contradicts_claim else "➖")
                    st.markdown(
                        f"- {icon} **{e.source_title}** "
                        f"(credibility: {e.credibility_score}/100): "
                        f"{e.snippet[:200]}..."
                    )
            else:
                st.warning("No evidence found for this claim.")

            # Citations
            if v.citations:
                st.markdown("**Citations:**")
                for cite in v.citations:
                    st.caption(f"📎 {cite}")

            # Reasoning
            if v.reasoning:
                with st.expander("📊 Score Breakdown"):
                    st.text(v.reasoning)

            # Risk notes
            if v.risk_notes:
                st.markdown("**Risk Notes:**")
                for note in v.risk_notes:
                    st.caption(f"⚠️ {note}")

    st.markdown("---")

    # Human Review Section
    flagged = [v for v in report.verdicts if v.human_review_required]
    if flagged:
        st.markdown("## ⚠️ Claims Requiring Human Review")
        st.warning(
            f"{len(flagged)} out of {report.total_claims} claims have been flagged "
            f"for human review due to insufficient evidence, low trust scores, "
            f"or high-risk domain content."
        )
        for v in flagged:
            st.markdown(
                f"- **{v.claim_id}**: {v.claim_text} "
                f"(Score: {v.trust_score}/100, Verdict: {v.verdict.value})"
            )

    st.markdown("---")

    # Full Report
    with st.expander("📄 Full Audit Report (Markdown)"):
        st.markdown(report.markdown_report)

    st.markdown("---")

    # Export Section
    st.markdown("## 📥 Export Report")

    exp1, exp2 = st.columns(2)

    with exp1:
        st.download_button(
            label="📝 Download Markdown Report",
            data=report.markdown_report,
            file_name=f"audit_report_{report.session_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with exp2:
        report_agent = ReportAgent()
        json_str = report_agent.to_json(report)
        st.download_button(
            label="📊 Download JSON Report",
            data=json_str,
            file_name=f"audit_report_{report.session_id}.json",
            mime="application/json",
            use_container_width=True,
        )
