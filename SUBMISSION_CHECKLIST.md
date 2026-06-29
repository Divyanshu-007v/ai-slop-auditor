# Submission Checklist — AI-Slop & Misinformation Auditor

**Deadline: July 6, 2026, 11:59 PM PT**

---

## ✅ Code & Functionality

- [ ] `pip install -r requirements.txt` succeeds with no errors
- [ ] `streamlit run app.py` starts without errors
- [ ] App works with **no API keys** set (offline mode)
- [ ] Sample article input produces extracted claims
- [ ] Sample transcript input produces extracted claims
- [ ] Sample social post input produces extracted claims
- [ ] Claims are correctly classified by type (medical, financial, political, etc.)
- [ ] Opinions and non-factual statements are filtered out
- [ ] Evidence is retrieved for known fixture claims
- [ ] Trust scores are computed and displayed
- [ ] Verdict labels are correct (Supported, Contradicted, etc.)
- [ ] Human review flags appear for low-confidence claims
- [ ] Export as Markdown works (download button)
- [ ] Export as JSON works (download button)
- [ ] Session memory persists across page refreshes
- [ ] Session history shows in sidebar

## ✅ Tests

- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] test_extraction.py — opinions filtered, claims classified
- [ ] test_scoring.py — trust score formula, verdict mapping
- [ ] test_guardrails.py — safety rules, human review flags
- [ ] test_no_evidence.py — insufficient evidence handling

## ✅ Capstone Concepts (minimum 3 required, all 7 demonstrated)

- [ ] **ADK-style multi-agent architecture** — 7 agents with orchestrator
- [ ] **MCP server/tool integration** — Tool registration and invocation
- [ ] **Agent skills** — Each agent has named skill
- [ ] **RAG-style retrieval** — Chunking + retrieval pipeline
- [ ] **Session memory** — SQLite persistence
- [ ] **Security guardrails** — Safety rules on every verdict
- [ ] **Human-in-the-loop** — Flagged claims for manual review

## ✅ Documentation

- [ ] README.md has project overview
- [ ] README.md has architecture diagram
- [ ] README.md has setup instructions
- [ ] README.md has capstone concepts table
- [ ] PROJECT_CONTEXT.md describes the project
- [ ] .env.example documents all optional variables

## ✅ Deliverables

- [ ] **Kaggle writeup** posted (under 2,500 words)
  - [ ] Problem statement
  - [ ] Approach description
  - [ ] Key concepts demonstrated
  - [ ] Results with examples
  - [ ] Limitations and future work
  - [ ] Links to GitHub and YouTube

- [ ] **YouTube demo** published (under 5 minutes, public)
  - [ ] Problem introduction
  - [ ] Architecture walkthrough
  - [ ] Live demo with sample input
  - [ ] Shows verdicts, scores, evidence
  - [ ] Shows session memory and export
  - [ ] Mentions capstone concepts

- [ ] **GitHub repository** is public
  - [ ] All source code committed
  - [ ] README with setup instructions
  - [ ] requirements.txt present
  - [ ] .env.example present (no real API keys)
  - [ ] No API keys or secrets in code
  - [ ] License file (optional)

## ✅ Final Checks

- [ ] No API keys or secrets committed to git
- [ ] .gitignore includes `.env`, `data/sessions.db`, `__pycache__/`, `.pytest_cache/`
- [ ] App runs on a fresh machine with just `pip install` and `streamlit run`
- [ ] Demo video is public and accessible
- [ ] Kaggle writeup is public and accessible
- [ ] All links in writeup and README are correct
- [ ] Submitted before **July 6, 2026, 11:59 PM PT**
