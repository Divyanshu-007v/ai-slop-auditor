# AI-Slop & Misinformation Auditor — Kaggle Writeup Draft

> **Word count target: Under 2,500 words**

---

## Problem Statement

The internet is experiencing an unprecedented flood of AI-generated misinformation. From fake medical advice claiming miracle cures, to fabricated financial predictions promising guaranteed returns, to misleading political content designed to manipulate public opinion — synthetic misinformation is becoming increasingly difficult to distinguish from legitimate information.

Existing fact-checking approaches suffer from three critical limitations:
1. **Manual effort** — Human fact-checkers cannot scale to match the volume of content being produced
2. **Hallucination risk** — AI systems that attempt to verify claims often fabricate sources or citations
3. **Opaque verdicts** — Most tools provide binary true/false judgments without explaining their reasoning

This project addresses these gaps with a **multi-agent claim auditing system** that provides transparent, explainable, and safety-conscious fact verification.

## Approach

### Multi-Agent Architecture

The system uses an ADK-style (Agent Development Kit) multi-agent architecture with seven specialized agents, each responsible for a distinct phase of the audit pipeline:

1. **Orchestrator Agent** — Coordinates the full pipeline and manages session state
2. **Extraction Agent** — Extracts factual claims from text, filtering out opinions and rhetoric
3. **Retrieval Agent** — Generates search queries and retrieves evidence via MCP tools
4. **Consensus Agent** — Compares claims against evidence and computes weighted trust scores
5. **Guardrail Agent** — Enforces safety rules and flags uncertain claims for human review
6. **Report Agent** — Generates comprehensive audit reports with export capabilities

### MCP Tool Integration

Evidence retrieval is handled through a Model Context Protocol (MCP)-style server that provides structured tool interfaces:
- `retrieve_local_evidence` — searches curated evidence fixtures
- `search_news`, `search_pubmed`, `search_factcheck` — extensible API tools
- `rank_sources` — ranks evidence by credibility and relevance

### RAG-Style Retrieval

The system implements a Retrieval-Augmented Generation (RAG) pipeline:
- Input text is chunked at sentence boundaries
- Claims are converted to search queries using keyword extraction
- Evidence is retrieved via MCP tools and ranked by TF-IDF-style matching
- Multiple evidence snippets are aggregated via a summary tree

### Trust Score Formula

Each claim receives a weighted trust score (0–100):

```
trust_score = 0.35 × source_credibility + 0.30 × evidence_agreement 
            + 0.15 × recency + 0.10 × claim_specificity + 0.10 × citation_quality
```

### Safety Guardrails

The Guardrail Agent enforces critical safety rules:
- Claims with trust scores below 85 are flagged for human review
- Medical, financial, and political claims receive domain-specific disclaimers
- Contradictory evidence triggers human review
- The system never fabricates sources or provides professional advice

## Key Concepts Demonstrated

[INSERT: Map each concept to specific implementation details]

1. **ADK-style multi-agent architecture** — 7 agents with defined roles and input/output contracts
2. **MCP server/tool integration** — Tool registration, schema introspection, structured invocation
3. **Agent skills** — Each agent has a named skill (claim_extract, evidence_fetch, adjudicate, etc.)
4. **RAG-style retrieval** — Chunking, keyword matching, evidence retrieval, summary aggregation
5. **Session memory** — SQLite persistence across sessions
6. **Security guardrails** — Safety rules preventing hallucination and overconfidence
7. **Human-in-the-loop** — Flagged claims displayed for manual review in UI

## Results

[INSERT: Screenshots and metrics from running the system on sample inputs]

### Sample Analysis: Health Misinformation Article

| Claim | Verdict | Trust Score |
|-------|---------|-------------|
| "Coffee cures diabetes" | ❌ Unsupported | 28/100 |
| "Apple Vision Pro launched Feb 2024" | ✅ Supported | 85/100 |
| "Vaccines do not cause autism" | ✅ Supported | 91/100 |
| "Drinking water prevents dehydration" | ✅ Supported | 93/100 |

### Test Suite Results
- **43 unit tests** — all passing
- Tests cover extraction, scoring, guardrails, and no-evidence edge cases

## Limitations

- Rule-based extraction may miss nuanced claims
- Evidence limited to local fixtures in MVP (no live APIs by default)
- English language only
- Text-only input (no image/video analysis)
- Not a replacement for professional fact-checkers

## Future Work

- Gemini LLM-powered claim extraction
- Live API integration (Google Fact Check, PubMed, News APIs)
- Standalone MCP server with stdio/SSE transport
- Multilingual support
- Browser extension for in-page auditing

---

**Links:**
- GitHub: [INSERT: URL]
- YouTube Demo: [INSERT: URL]
