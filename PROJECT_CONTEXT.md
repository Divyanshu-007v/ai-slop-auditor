# PROJECT CONTEXT — AI-Slop & Misinformation Auditor

## What Is This?

A multi-agent claim auditing system that takes long-form text (articles, transcripts, social media posts), extracts factual claims, retrieves evidence from trusted sources, computes explainable trust scores, and flags uncertain claims for human review.

## Why Does This Exist?

The internet is flooded with AI-generated misinformation: fake medical advice, fake financial predictions, misleading political posts, and synthetic content. This project provides a structured, transparent way to audit text for factual accuracy — without guessing or hallucinating answers.

## Capstone Concepts Demonstrated

1. **ADK-style multi-agent architecture** — 7 specialized agents with orchestrator coordination
2. **MCP server/tool integration** — FastMCP-style evidence server with tool registration
3. **Agent skills** — Each agent has defined skills (extraction, retrieval, consensus, guardrails, reporting)
4. **RAG-style evidence retrieval** — Text chunking, keyword matching, evidence retrieval pipeline
5. **Session memory** — SQLite-backed persistent memory across sessions
6. **Security guardrails** — Safety rules preventing hallucinated citations and overconfident outputs
7. **Human-in-the-loop review** — Low-confidence claims flagged for manual review

## Architecture

```
User Input → Orchestrator → Extraction → Retrieval → MCP Server
           → Consensus → Guardrails → Report → Final Audit Report
```

## Key Design Decisions

- **Offline-first**: Works fully without API keys using local JSON evidence fixtures
- **Rule-based extraction default**: No LLM required; Gemini is optional enhancement
- **In-process MCP server**: Follows MCP patterns but runs in-process for MVP simplicity
- **SQLite session memory**: Lightweight, no external database required
- **Pydantic data models**: Type-safe contracts shared across all agents

## Deadline

July 6, 2026, 11:59 PM PT

## Deliverables

- Kaggle writeup (under 2,500 words)
- YouTube demo (under 5 minutes)
- Public GitHub repository with setup instructions
