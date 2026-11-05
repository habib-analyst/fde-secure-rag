import pytest

from fde_secure_rag.citations import (
    CitationError, assert_citations_valid, compose_answer, verify_citations)
from fde_secure_rag.fixtures import ALICE
from fde_secure_rag.models import Chunk


def _chunk(chunk_id, text):
    doc_id = chunk_id.split("#")[0]
    return Chunk(chunk_id=chunk_id, doc_id=doc_id, tenant_id="t",
                 text=text, position=0)


def test_verifier_accepts_valid_answer():
    results = [(_chunk("doc-a#chunk_0", "alpha text"), 0.9),
               (_chunk("doc-a#chunk_1", "beta text"), 0.5)]
    answer = compose_answer(results)
    assert "[doc-a#chunk_0]" in answer and "[doc-a#chunk_1]" in answer
    assert verify_citations(answer, ["doc-a#chunk_0", "doc-a#chunk_1"])
    assert_citations_valid(answer, ["doc-a#chunk_0", "doc-a#chunk_1"])


def test_verifier_rejects_tampered_citation():
    results = [(_chunk("doc-a#chunk_0", "alpha text"), 0.9)]
    answer = compose_answer(results)
    tampered = answer.replace("doc-a#chunk_0", "doc-beta-refund#chunk_0")
    allowed = ["doc-a#chunk_0"]
    assert not verify_citations(tampered, allowed)
    with pytest.raises(CitationError):
        assert_citations_valid(tampered, allowed)


def test_verifier_rejects_answer_with_no_citations():
    assert not verify_citations("an answer with no citations at all",
                                ["doc-a#chunk_0"])


def test_service_answer_citations_are_all_retrieved(service):
    resp = service.query(ALICE, "refund policy customers annual", top_k=3)
    assert resp["citations"] == [r["chunk_id"] for r in resp["results"]]
    assert verify_citations(resp["answer"], resp["citations"])
    for chunk_id in resp["citations"]:
        assert f"[{chunk_id}]" in resp["answer"]
