"""TF-IDF ranking over a *pre-filtered* chunk set.

Security invariant: the retriever is only ever constructed from chunks
the caller is permitted to see. Document frequencies and IDF are computed
over that permitted set alone, so a filtered-out chunk cannot influence
any score — not even indirectly through corpus statistics.

Uses scikit-learn's TfidfVectorizer when it is importable; otherwise a
stdlib TF-IDF implementation with the same ranking semantics
(sublinear-free tf, smoothed idf, cosine similarity).
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .models import Chunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


try:  # pragma: no cover - exercised implicitly depending on environment
    from sklearn.feature_extraction.text import TfidfVectorizer as _SkVectorizer
    HAS_SKLEARN = True
except Exception:  # pragma: no cover
    _SkVectorizer = None
    HAS_SKLEARN = False


class TfidfRetriever:
    """Rank a fixed, already-permission-filtered list of chunks."""

    def __init__(self, chunks: list[Chunk]):
        self.chunks = list(chunks)
        self._sklearn = None
        self._matrix = None
        self._idf: dict[str, float] = {}
        self._vectors: list[dict[str, float]] = []
        if not self.chunks:
            return
        texts = [c.text for c in self.chunks]
        if HAS_SKLEARN:
            try:
                vec = _SkVectorizer(token_pattern=r"(?u)\b[a-z0-9]+\b")
                self._matrix = vec.fit_transform(texts)
                self._sklearn = vec
                return
            except ValueError:
                self._sklearn = None
                self._matrix = None
        # Stdlib fallback.
        tokenized = [tokenize(t) for t in texts]
        n = len(texts)
        df: Counter[str] = Counter()
        for toks in tokenized:
            df.update(set(toks))
        self._idf = {
            term: math.log((1 + n) / (1 + count)) + 1.0
            for term, count in df.items()
        }
        self._vectors = [self._vectorize(toks) for toks in tokenized]

    def _vectorize(self, toks: list[str]) -> dict[str, float]:
        counts = Counter(toks)
        vec = {t: c * self._idf.get(t, 0.0) for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, query: str, top_k: int = 3) -> list[tuple[Chunk, float]]:
        """Return [(chunk, score), ...] sorted by score desc, then chunk_id.

        Chunks with a zero score (no token overlap) are not returned.
        """
        if not self.chunks or top_k <= 0:
            return []
        if self._sklearn is not None:
            q = self._sklearn.transform([query])
            scores = (self._matrix @ q.T).toarray().ravel()
            scored = [
                (self.chunks[i], float(scores[i]))
                for i in range(len(self.chunks)) if scores[i] > 0
            ]
        else:
            qvec = self._vectorize(tokenize(query))
            scored = []
            for chunk, vec in zip(self.chunks, self._vectors):
                score = sum(qvec.get(t, 0.0) * v for t, v in vec.items())
                if score > 0:
                    scored.append((chunk, score))
        scored.sort(key=lambda item: (-item[1], item[0].chunk_id))
        return scored[:top_k]
