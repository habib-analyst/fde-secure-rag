"""Deterministic chunking: fixed-size word windows with fixed overlap.

The same input text always produces the same chunks, in the same order,
with the same ids. There is no randomness, no model, and no state.
"""
from __future__ import annotations

CHUNK_WORDS = 50
OVERLAP_WORDS = 10
STEP_WORDS = CHUNK_WORDS - OVERLAP_WORDS  # 40


def chunk_text(text: str, chunk_words: int = CHUNK_WORDS,
               overlap_words: int = OVERLAP_WORDS) -> list[str]:
    """Split *text* into deterministic word windows.

    Windows are `chunk_words` words wide, advancing `chunk_words -
    overlap_words` words at a time. The final window may be shorter.
    Empty / whitespace-only text yields no chunks.
    """
    if chunk_words <= 0:
        raise ValueError("chunk_words must be positive")
    if overlap_words < 0 or overlap_words >= chunk_words:
        raise ValueError("overlap_words must satisfy 0 <= overlap < chunk_words")
    words = text.split()
    if not words:
        return []
    step = chunk_words - overlap_words
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunks.append(" ".join(words[start:start + chunk_words]))
        if start + chunk_words >= len(words):
            break
        start += step
    return chunks


def chunk_document(doc_id: str, text: str, **kwargs) -> list[tuple[str, str]]:
    """Return [(chunk_id, chunk_text), ...] with stable ids doc_id#chunk_n."""
    return [
        (f"{doc_id}#chunk_{i}", chunk)
        for i, chunk in enumerate(chunk_text(text, **kwargs))
    ]
