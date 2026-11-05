from fde_secure_rag.fixtures import ALICE, CAROL, TENANT_BETA
from fde_secure_rag.models import Document


def test_ranking_sanity_known_query_retrieves_known_doc_first(service):
    resp = service.query(ALICE, "full refund within 30 days annual plans",
                         top_k=3)
    assert resp["results"], "expected at least one result"
    assert resp["results"][0]["doc_id"] == "doc-alpha-refund"
    assert resp["results"][0]["score"] > 0


def test_ranking_sanity_beta_gets_beta_terms(service):
    resp = service.query(CAROL, "partial refund 14 days monthly plans",
                         top_k=3)
    assert resp["results"][0]["doc_id"] == "doc-beta-refund"


def test_filtered_chunks_do_not_influence_scores(service):
    """Filter-before-rank: adding a query-heavy foreign document must not
    change the scores of the caller's permitted chunks (IDF is computed
    over the permitted corpus only)."""
    before = service.query(ALICE, "refund policy customers plans", top_k=3)
    scores_before = {r["chunk_id"]: r["score"] for r in before["results"]}

    noisy = Document(
        doc_id="doc-beta-refund-spam", tenant_id=TENANT_BETA,
        title="Refund Policy", acl_type="tenant", sensitivity="internal",
        content=("refund policy customers plans refund policy customers "
                 "plans refund refund refund policy policy customers"))
    service.ingest(noisy, CAROL)

    after = service.query(ALICE, "refund policy customers plans", top_k=3)
    scores_after = {r["chunk_id"]: r["score"] for r in after["results"]}
    assert scores_after == scores_before


def test_no_match_returns_empty_results_and_plain_answer(service):
    resp = service.query(ALICE, "zzzqqq nonexistentterm", top_k=3)
    assert resp["results"] == []
    assert resp["citations"] == []
    assert resp["answer"] == "No permitted documents matched the query."
