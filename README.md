# 🔍 AI-Slop & Misinformation Auditor

A multi-agent claim auditing system that takes long-form text (articles, transcripts, social media posts), extracts factual claims, retrieves evidence from trusted sources, computes explainable trust scores, and flags uncertain claims for human review.

> **⚖️ Disclaimer:** This is an auditing assistant, not a final authority. Results should be independently verified by domain experts. The system does not provide medical, legal, or financial advice.

---

## 🎯 Problem Statement

The internet is flooded with AI-generated misinformation: fake medical advice, fake financial predictions, misleading political posts, and synthetic content. Existing fact-checking tools either require manual effort, hallucinate sources, or give overconfident verdicts without transparency.

This project provides a **structured, transparent, and explainable** approach to auditing text for factual accuracy — without guessing or fabricating evidence.

---

## 📚 Capstone Concepts Demonstrated

| # | Concept | Implementation | Key Files |
|---|---------|---------------|-----------|
| 1 | **ADK-style multi-agent architecture** | 7 specialized agents (Orchestrator, Extraction, Retrieval, Consensus, Guardrail, Report) coordinated via pipeline | `agents/*.py` |
| 2 | **MCP server/tool integration** | FastMCP-style evidence server with tool registration, schema introspection, and structured invocation; upgrade-ready for standalone MCP | `mcp_server/server.py`, `mcp_server/tools.py` |
| 3 | **Agent skills** | Each agent exposes distinct skills: `claim_extract`, `evidence_fetch`, `adjudicate`, `safety_check`, `report_gen` | All agent files |
| 4 | **RAG-style evidence retrieval** | Text chunking → keyword matching → evidence retrieval → summary tree aggregation | `rag/chunker.py`, `rag/retriever.py`, `rag/summary_tree.py` |
| 5 | **Session memory** | SQLite-backed persistent memory stores claims, evidence, and verdicts across sessions | `memory/session_memory.py` |
| 6 | **Security guardrails** | Prevents hallucinated citations, overconfident outputs, and unsafe advice; adds domain disclaimers | `agents/guardrail_agent.py` |
| 7 | **Human-in-the-loop review** | Low-confidence claims flagged with `human_review_required`; Streamlit UI highlights them for manual review | `agents/guardrail_agent.py`, `app.py` |

---

## 🏗️ Architecture

```
User Input (Streamlit UI)
    │
    ▼
┌──────────────────────────┐
│   Orchestrator Agent      │ ── controls full pipeline, manages session
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│   Extraction Agent        │ ── rule-based (offline) or Gemini LLM (optional)
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│   Retrieval Agent         │ ── generates queries, selects MCP tools
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────────┐
│   MCP Evidence Server         │ ── local fixtures + optional live APIs
│   Tools: retrieve_local,      │
│   search_news, search_pubmed, │
│   search_factcheck, rank      │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────┐
│   Consensus Agent         │ ── compares claim vs evidence, scores
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│   Guardrail Agent         │ ── enforces safety rules, flags for review
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│   Report Agent            │ ── generates final audit report (MD + JSON)
└────────┬─────────────────┘
         │
         ▼
   Final Audit Report
   (Streamlit display + Markdown/JSON export)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+

### Setup
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/ai-slop-auditor.git
cd ai-slop-auditor

# Install dependencies
pip install -r requirements.txt

# (Optional) Copy and configure environment variables
cp .env.example .env
# Edit .env to add GOOGLE_API_KEY for Gemini-powered extraction
```

### Run
```bash
streamlit run app.py
```

### Test
```bash
# Run all tests
python -m pytest tests/ -v

# Run evaluation
python evaluation/eval_runner.py
```

---

## 📝 How to Use

1. **Open the app** at `http://localhost:8501`
2. **Paste text** — article, transcript, or social media post
3. **Or select a sample** from the dropdown
4. **Click "🔍 Analyze Claims"**
5. **Review results:**
   - Extracted claims with type badges
   - Evidence for each claim with sources
   - Trust scores (0–100) with color-coded bars
   - Verdict labels (Supported, Contradicted, etc.)
   - Human review flags for uncertain claims
6. **Export** — Download as Markdown or JSON

---

## 📂 Project Structure

```
ai-slop-auditor/
├── app.py                          # Streamlit UI
├── models.py                       # Pydantic data models
├── requirements.txt                # Dependencies
├── .env.example                    # Optional env vars
├── agents/
│   ├── orchestrator_agent.py       # Pipeline coordinator
│   ├── extraction_agent.py         # Claim extraction (rule-based + Gemini)
│   ├── retrieval_agent.py          # Evidence retrieval via MCP
│   ├── consensus_agent.py          # Claim vs evidence adjudication
│   ├── guardrail_agent.py          # Safety rules & human review
│   └── report_agent.py            # Report generation
├── mcp_server/
│   ├── server.py                   # MCP-style evidence server
│   ├── tools.py                    # MCP tool implementations
│   └── source_ranker.py           # Evidence ranking
├── rag/
│   ├── chunker.py                  # Text chunking
│   ├── retriever.py               # Evidence retrieval pipeline
│   └── summary_tree.py            # Evidence summarization
├── memory/
│   └── session_memory.py          # SQLite session persistence
├── data/
│   ├── trusted_sources/           # Evidence fixtures & credibility scores
│   └── sample_inputs/             # Sample articles, transcripts, posts
├── evaluation/                    # Test claims & evaluation runner
└── tests/                        # pytest test suite (43 tests)
```

---

## 🧪 Sample Inputs

| Sample | Description | Expected Results |
|--------|-------------|-----------------|
| **Sample Article** | Health + tech claims mixed with opinions | Coffee/diabetes claim contradicted, Vision Pro claim supported |
| **Sample Transcript** | Financial/crypto video with hype | Bitcoin guarantee unsupported, Fed rate facts supported |
| **Sample Social Post** | Conspiracy post with misinformation | Vaccines/autism contradicted, 5G/cancer contradicted |

---

## 🔧 Trust Score Formula

```
trust_score = 0.35 × source_credibility_score
            + 0.30 × evidence_agreement_score
            + 0.15 × recency_score
            + 0.10 × claim_specificity_score
            + 0.10 × citation_quality_score
```

| Score Range | Verdict |
|-------------|---------|
| 90–100 | ✅ Supported |
| 75–89 | 🟡 Mostly Supported |
| 50–74 | 🟠 Partially Supported |
| 25–49 | ❌ Unsupported |
| 0–24 | 🔴 Contradicted |

---

## ⚖️ Limitations

- **Rule-based extraction** may miss nuanced claims or include non-claims
- **Local fixtures only** — evidence is limited to pre-built entries in MVP mode
- **No real-time fact-checking** — live APIs are optional and not configured by default
- **English only** — no multilingual support
- **No image/video analysis** — text-only input
- Not a replacement for professional fact-checkers or domain experts

---

## 🔮 Future Work

- Gemini-powered claim extraction (enhanced mode)
- Live API integration (Google Fact Check, PubMed, News APIs)
- Standalone MCP server (stdio/SSE transport)
- Browser extension for in-page auditing
- Multilingual support
- Image/video content analysis
- User accounts and shared audit history
- Fine-tuned claim extraction model

---

## 🎬 Demo Script Outline

1. **0:00–0:30** — Problem: misinformation flooding the internet
2. **0:30–1:00** — Architecture walkthrough (agent pipeline)
3. **1:00–2:30** — Live demo: paste sample article, analyze
4. **2:30–3:30** — Show verdicts, trust scores, evidence, citations
5. **3:30–4:15** — Session memory, export Markdown/JSON
6. **4:15–4:45** — Capstone concepts demonstrated
7. **4:45–5:00** — Limitations, future work, closing

---

## 📜 License

This project is created for educational/capstone purposes.
