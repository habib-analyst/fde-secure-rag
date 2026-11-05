import json

from fde_secure_rag.fixtures import ALICE, BOB, CAROL, DAVE, SEED_DOCS

BETA_REFUND_TEXT = next(
    d.content for d in SEED_DOCS if d.doc_id == "doc-beta-refund")


def _doc_ids(response):
    return {r["doc_id"] for r in response["results"]}


def test_cross_tenant_retrieval_impossible_on_exact_match(service):
    # The query IS the beta tenant's refund document, word for word.
    resp = service.query(ALICE, BETA_REFUND_TEXT, top_k=5)
    assert "doc-beta-refund" not in _doc_ids(resp)
    assert all(not r["chunk_id"].startswith("doc-beta")
               for r in resp["results"])
    # Check results + answer only: the response also echoes the query
    # text itself, which is the caller's own input, not leaked data.
    blob = json.dumps(resp["results"]) + resp["answer"]
    assert "doc-beta" not in blob
    assert "14 days" not in blob and "partial refund" not in blob.lower()


def test_cross_tenant_reverse_direction(service):
    resp = service.query(CAROL, "full refund within 30 days annual plans",
                         top_k=5)
    assert _doc_ids(resp) <= {"doc-beta-refund", "doc-beta-finance"}
    blob = json.dumps(resp["results"]) + resp["answer"]
    assert "30 days" not in blob


def test_tenant_wide_acl_allows_any_user_in_tenant(service):
    resp = service.query(DAVE, "refund policy customers annual plans",
                         top_k=3)
    assert "doc-alpha-refund" in _doc_ids(resp)


def test_group_acl_allows_member(service):
    resp = service.query(
        ALICE, "invoice disputes chargeback payment processor", top_k=3)
    assert "doc-alpha-billing" in _doc_ids(resp)


def test_group_acl_denies_non_member(service):
    resp = service.query(
        BOB, "invoice disputes chargeback payment processor", top_k=5)
    assert "doc-alpha-billing" not in _doc_ids(resp)
    blob = json.dumps(resp["results"]) + resp["answer"]
    assert "five thousand" not in blob


def test_user_acl_allows_named_user(service):
    resp = service.query(
        ALICE, "harbor acquisition board approved closed session", top_k=3)
    assert "doc-alpha-executive" in _doc_ids(resp)


def test_user_acl_denies_other_users_in_same_tenant(service):
    resp = service.query(
        BOB, "harbor acquisition board approved closed session", top_k=5)
    assert "doc-alpha-executive" not in _doc_ids(resp)
    blob = json.dumps(resp["results"]) + resp["answer"]
    assert "harbor" not in blob.lower()
