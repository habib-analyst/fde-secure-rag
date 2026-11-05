import json

from fde_secure_rag.fixtures import ALICE, BOB


def test_ingest_events_are_audited(service):
    ingests = service.audit_log("ingest")
    assert len(ingests) == 6  # the six seeded documents
    assert {e["doc_ids"][0] for e in ingests} == {
        "doc-alpha-refund", "doc-beta-refund", "doc-alpha-billing",
        "doc-alpha-support", "doc-alpha-executive", "doc-beta-finance"}


def test_every_query_writes_an_audit_entry(service):
    before = len(service.audit_log("query"))
    service.query(ALICE, "refund policy", top_k=2)
    service.query(BOB, "support playbook triage", top_k=2)
    entries = service.audit_log("query")
    assert len(entries) == before + 2
    assert entries[-1]["actor_user"] == "fixture-user-bob"
    assert entries[-1]["tenant_id"] == "fixture-tenant-alpha"
    assert entries[-1]["result_count"] >= 1


def test_denied_doc_ids_in_audit_but_never_in_response(service):
    resp = service.query(
        ALICE, "partial refund credited as account balance cannot "
               "be withdrawn", top_k=3)
    # Nothing about the denied document leaks into the response.
    assert "doc-beta-refund" not in json.dumps(resp)

    queries = service.audit_log("query")
    assert "doc-beta-refund" in queries[-1]["denied_doc_ids"]
    denies = service.audit_log("deny")
    assert denies and "doc-beta-refund" in denies[-1]["denied_doc_ids"]
    assert denies[-1]["actor_user"] == "fixture-user-alice"


def test_group_denial_is_audited(service):
    service.query(BOB, "invoice disputes chargeback payment processor",
                  top_k=3)
    queries = service.audit_log("query")
    assert "doc-alpha-billing" in queries[-1]["denied_doc_ids"]
