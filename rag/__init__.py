"""RAG (Retrieval-Augmented Generation) module for the AI-Slop & Misinformation Auditor."""

from rag.chunker import chunk_text
from rag.retriever import EvidenceRetriever
from rag.summary_tree import SummaryTree

__all__ = ["chunk_text", "EvidenceRetriever", "SummaryTree"]
