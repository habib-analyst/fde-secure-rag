import json

from conftest import headers
from fde_secure_rag.fixtures import ALICE, BOB, CAROL


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_api_ingest_and_query_round_trip(client):
    r = client.post("/documents", headers=headers(ALICE), json={
        "doc_id": "doc-api-onboarding", "title": "Onboarding",
        "content": "Onboarding checklist. New engineers pair with a "
                   "buddy and ship a small change in week one.",
        "acl_type": "tenant", "sensitivity": "internal"})
    assert r.status_code == 201, r.text
    assert r.json()["chunk_ids"] == ["doc-api-onboarding#chunk_0"]

    q = client.post("/query", headers=headers(ALICE),
                    json={"query": "onboarding checklist buddy week one",
                          "top_k": 2})
    assert q.status_code == 200, q.text
    body = q.json()
    assert body["results"][0]["doc_id"] == "doc-api-onboarding"
    assert body["citations"] == [r["chunk_id"] for r in body["results"]]


def test_api_cross_tenant_query_returns_no_beta_data(client):
    q = client.post("/query", headers=headers(ALICE), json={
        "query": "partial refund within 14 days monthly plans credited "
                 "as account balance", "top_k": 5})
    assert q.status_code == 200
    assert "doc-beta" not in json.dumps(q.json())


def test_api_group_denied_user_gets_no_billing_doc(client):
    q = client.post("/query", headers=headers(BOB), json={
        "query": "invoice disputes chargeback payment processor",
        "top_k": 5})
    assert q.status_code == 200
    assert "doc-alpha-billing" not in json.dumps(q.json())


def test_api_ingest_validation_error_is_422(client):
    r = client.post("/documents", headers=headers(ALICE), json={
        "doc_id": "doc-bad", "title": "Bad", "content": "content",
        "acl_type": "groups", "acl_groups": []})
    assert r.status_code == 422


def test_api_audit_endpoint_shows_query_and_deny(client):
    client.post("/query", headers=headers(CAROL), json={
        "query": "full refund within 30 days annual plans", "top_k": 3})
    r = client.get("/audit")
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert any(e["event_type"] == "query" for e in entries)
    deny = [e for e in entries if e["event_type"] == "deny"]
    assert deny and "doc-alpha-refund" in deny[-1]["denied_doc_ids"]
