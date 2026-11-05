"""Data model and ACL validation for fde-secure-rag."""
from __future__ import annotations

from dataclasses import dataclass, field

ACL_TYPES = ("tenant", "groups", "users")
SENSITIVITY_LABELS = ("internal", "confidential", "restricted")


class IngestValidationError(ValueError):
    """Raised when document / ACL metadata fails validation."""


@dataclass
class Identity:
    """Caller identity, supplied via fixture auth headers in the API."""
    tenant_id: str
    user_id: str
    groups: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.tenant_id or not str(self.tenant_id).strip():
            raise IngestValidationError("identity requires a tenant_id")
        if not self.user_id or not str(self.user_id).strip():
            raise IngestValidationError("identity requires a user_id")
        self.groups = tuple(self.groups or ())


@dataclass
class Document:
    doc_id: str
    tenant_id: str
    title: str
    content: str
    acl_type: str = "tenant"
    acl_groups: tuple[str, ...] = ()
    acl_users: tuple[str, ...] = ()
    sensitivity: str = "internal"
    created_by: str = ""

    def validate(self) -> None:
        if not self.doc_id or not str(self.doc_id).strip():
            raise IngestValidationError("doc_id is required")
        if not self.tenant_id or not str(self.tenant_id).strip():
            raise IngestValidationError("tenant_id is required")
        if not self.title or not str(self.title).strip():
            raise IngestValidationError("title is required")
        if not self.content or not str(self.content).strip():
            raise IngestValidationError("content is required")
        if self.acl_type not in ACL_TYPES:
            raise IngestValidationError(
                f"acl_type must be one of {ACL_TYPES}, got {self.acl_type!r}")
        if self.acl_type == "groups" and not self.acl_groups:
            raise IngestValidationError(
                "acl_type='groups' requires at least one acl_groups entry")
        if self.acl_type == "users" and not self.acl_users:
            raise IngestValidationError(
                "acl_type='users' requires at least one acl_users entry")
        if self.acl_type == "tenant" and (self.acl_groups or self.acl_users):
            raise IngestValidationError(
                "acl_type='tenant' must not set acl_groups or acl_users")
        if self.sensitivity not in SENSITIVITY_LABELS:
            raise IngestValidationError(
                f"sensitivity must be one of {SENSITIVITY_LABELS}, "
                f"got {self.sensitivity!r}")


@dataclass
class Chunk:
    chunk_id: str  # doc_id#chunk_n
    doc_id: str
    tenant_id: str
    text: str
    position: int


def can_access(doc: Document, identity: Identity) -> bool:
    """The single permission predicate. Tenant boundary is absolute."""
    if doc.tenant_id != identity.tenant_id:
        return False
    if doc.acl_type == "tenant":
        return True
    if doc.acl_type == "groups":
        return bool(set(doc.acl_groups) & set(identity.groups))
    if doc.acl_type == "users":
        return identity.user_id in doc.acl_users
    return False  # unknown ACL types deny by default; validate() prevents them
