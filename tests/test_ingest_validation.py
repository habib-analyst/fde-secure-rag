import pytest

from fde_secure_rag.fixtures import ALICE, TENANT_BETA
from fde_secure_rag.models import Document, IngestValidationError


def _doc(**overrides):
    base = dict(doc_id="doc-new", tenant_id=ALICE.tenant_id,
                title="New Doc", content="some content here",
                acl_type="tenant", sensitivity="internal")
    base.update(overrides)
    return Document(**base)


def test_valid_ingest_returns_chunk_ids(empty_service):
    out = empty_service.ingest(_doc(), ALICE)
    assert out["chunk_ids"] == ["doc-new#chunk_0"]
    assert out["chunk_count"] == 1


@pytest.mark.parametrize("overrides", [
    {"acl_type": "groups"},                              # groups, none given
    {"acl_type": "users"},                               # users, none given
    {"acl_type": "everyone"},                            # unknown acl type
    {"acl_type": "tenant", "acl_groups": ("g1",)},       # tenant + groups
    {"sensitivity": "top-secret"},                       # unknown label
    {"content": "   "},                                  # empty content
    {"title": ""},                                       # empty title
    {"tenant_id": ""},                                   # empty tenant
])
def test_ingest_validation_errors(empty_service, overrides):
    with pytest.raises(IngestValidationError):
        empty_service.ingest(_doc(**overrides), ALICE)


def test_cross_tenant_ingest_is_rejected(empty_service):
    with pytest.raises(IngestValidationError):
        empty_service.ingest(_doc(tenant_id=TENANT_BETA), ALICE)


def test_failed_ingest_writes_no_document_or_audit(empty_service):
    with pytest.raises(IngestValidationError):
        empty_service.ingest(_doc(acl_type="groups"), ALICE)
    assert empty_service.store.all_documents() == []
    assert empty_service.audit_log("ingest") == []
