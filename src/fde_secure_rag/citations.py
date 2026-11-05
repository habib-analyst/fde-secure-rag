"""Citation extraction, answer composition, and citation verification.

An answer may only cite chunks that were actually retrieved for this
caller from the permitted set. The verifier is independent of the
composer: it re-checks every citation in the final answer text against
the retrieved set, so a tampered or hallucinated citation is rejected.
"""
from __future__ import annotations

import re

_CITATION_RE = re.compile(r"\[([^\[\]\s]+#chunk_\d+)\]")


class CitationError(ValueError):
    """Raised when an answer cites a chunk outside the retrieved set."""


def extract_citations(answer: str) -> list[str]:
    return _CITATION_RE.findall(answer or "")


def compose_answer(results: list[tuple[object, float]]) -> str:
    """Extractive answer: the retrieved chunk texts, each with its citation.

    No text is generated. Every sentence in the answer is a retrieved
    chunk, verbatim, followed by its [chunk_id] citation.
    """
    if not results:
        return "No permitted documents matched the query."
    parts = [f"{chunk.text} [{chunk.chunk_id}]" for chunk, _score in results]
    return " ".join(parts)


def verify_citations(answer: str, retrieved_chunk_ids) -> bool:
    """True iff the answer cites at least one chunk and every citation
    is in *retrieved_chunk_ids*."""
    cited = extract_citations(answer)
    if not cited:
        return False
    allowed = set(retrieved_chunk_ids)
    return all(c in allowed for c in cited)


def assert_citations_valid(answer: str, retrieved_chunk_ids) -> None:
    if not verify_citations(answer, retrieved_chunk_ids):
        cited = extract_citations(answer)
        bad = [c for c in cited if c not in set(retrieved_chunk_ids)]
        raise CitationError(
            f"answer cites chunks outside the retrieved permitted set: {bad}")
