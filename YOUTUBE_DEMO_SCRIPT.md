# YouTube Demo Script — AI-Slop & Misinformation Auditor

> **Total duration: Under 5 minutes**

---

## 0:00–0:30 — Problem Introduction

**[Screen: Title slide or intro graphic]**

> "The internet is flooded with AI-generated misinformation — fake medical advice, fabricated financial predictions, misleading political claims. The problem isn't just that misinformation exists, it's that it's becoming increasingly convincing and difficult to detect."

> "I built the AI-Slop & Misinformation Auditor — a multi-agent system that analyzes text, extracts factual claims, retrieves evidence, and gives you transparent, explainable trust scores. Let me show you how it works."

---

## 0:30–1:00 — Architecture Walkthrough

**[Screen: Architecture diagram]**

> "The system uses seven specialized agents in a pipeline."

Walk through briefly:
1. **Orchestrator** controls the flow
2. **Extraction Agent** pulls out factual claims, ignoring opinions
3. **Retrieval Agent** searches for evidence via an MCP Evidence Server
4. **Consensus Agent** computes trust scores using a weighted formula
5. **Guardrail Agent** flags uncertain claims for human review
6. **Report Agent** generates the final report

> "Each agent has a specific skill and communicates through structured data contracts. The MCP Evidence Server provides tool-based evidence retrieval — just like the Model Context Protocol standard."

---

## 1:00–2:30 — Live Demo: Analyze Sample Article

**[Screen: Streamlit app running in browser]**

1. Show the app interface — title, text input area, sample selector
2. Point out the extraction mode indicator (rule-based or Gemini)
3. Select "Sample Article" from the dropdown
4. Show the sample text — it mixes factual claims with opinions
5. Click "🔍 Analyze Claims"
6. Show the progress bar as each agent processes

> "Watch as each agent does its work — extracting claims, retrieving evidence, computing scores, applying safety guardrails."

7. Show the summary metrics: total claims, supported, unsupported, flagged
8. Scroll through the extracted claims

> "Notice how the system correctly ignores opinions like 'I think coffee is great' and focuses on verifiable claims like 'Coffee cures diabetes'."

---

## 2:30–3:30 — Verdicts, Scores, and Evidence

**[Screen: Claim-by-claim results]**

Walk through 2-3 specific claims:

### Claim: "Coffee cures diabetes"
> "This medical claim gets a low trust score — the evidence from peer-reviewed journals says coffee may reduce risk but doesn't cure diabetes. Verdict: Unsupported. Flagged for human review."

### Claim: "Apple launched Vision Pro in February 2024"
> "This gets a high trust score — two credible sources confirm the launch date. Verdict: Supported."

### Claim: "Vaccines do not cause autism"
> "Strong evidence from CDC and peer-reviewed studies. High trust score. Supported."

Show:
- Color-coded verdict badges
- Trust score progress bars
- Evidence snippets with source attribution
- Citations
- Risk notes and disclaimers

---

## 3:30–4:15 — Session Memory & Export

**[Screen: Sidebar and export section]**

> "The system stores every audit session in SQLite memory. You can see past sessions in the sidebar."

Show the session history sidebar.

> "And you can export the full report as Markdown or JSON for documentation."

Click both download buttons and briefly show the files.

---

## 4:15–4:45 — Capstone Concepts

**[Screen: Sidebar showing concepts list]**

Quickly mention the 7 concepts:
> "This project demonstrates seven key concepts from the course:
> 1. ADK-style multi-agent architecture
> 2. MCP server and tool integration
> 3. Agent skills
> 4. RAG-style evidence retrieval
> 5. Session memory with SQLite
> 6. Security guardrails
> 7. Human-in-the-loop review"

> "All 43 unit tests pass, and the system works completely offline with no API keys required."

---

## 4:45–5:00 — Closing

> "The AI-Slop & Misinformation Auditor is a working MVP that brings transparency and explainability to fact-checking. It doesn't guess — it retrieves evidence, computes scores, and flags uncertain claims for human review."

> "Future work includes Gemini-powered extraction, live API integration, and a standalone MCP server."

> "Check out the GitHub repo and Kaggle writeup linked below. Thanks for watching!"

**[Screen: Links to GitHub, Kaggle, end screen]**
