"""
Text Chunker — splits long input text into manageable, overlapping chunks.

Used by the Extraction Agent to handle long-form articles, transcripts,
and posts. Sentence-boundary aware to avoid splitting mid-sentence.
"""

from __future__ import annotations

import re


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """
    Split text into overlapping chunks at sentence boundaries.

    Args:
        text: The input text to chunk.
        chunk_size: Target number of characters per chunk.
        overlap: Number of characters of overlap between chunks.

    Returns:
        List of text chunks. If the text is shorter than chunk_size,
        returns [text] as a single-element list.
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    # If text is short enough, return as single chunk
    if len(text) <= chunk_size:
        return [text]

    # Split into sentences (handles ., !, ? followed by space or newline)
    sentences = re.split(r"(?<=[.!?])\s+", text)

    # Remove empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # If adding this sentence exceeds chunk_size, finalize current chunk
        if current_length + sentence_len > chunk_size and current_chunk:
            chunk_text_str = " ".join(current_chunk)
            chunks.append(chunk_text_str)

            # Compute overlap: keep trailing sentences that fit in overlap
            overlap_sentences: list[str] = []
            overlap_len = 0
            for s in reversed(current_chunk):
                if overlap_len + len(s) <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s) + 1  # +1 for space
                else:
                    break

            current_chunk = overlap_sentences
            current_length = sum(len(s) for s in current_chunk) + max(0, len(current_chunk) - 1)

        current_chunk.append(sentence)
        current_length += sentence_len + (1 if current_chunk else 0)

    # Don't forget the last chunk
    if current_chunk:
        chunk_text_str = " ".join(current_chunk)
        chunks.append(chunk_text_str)

    return chunks
