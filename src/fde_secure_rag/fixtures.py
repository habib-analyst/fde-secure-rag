"""Seeded synthetic corpus: two tenants, overlapping vocabulary.

Both tenants have a "Refund Policy" document with the same topic words
and different terms, so a permission bug would be visible immediately:
an alpha user asking about refunds must get alpha's 30-day terms,
never beta's 14-day terms. All identities and ids are synthetic
`fixture-*` values.
"""
from __future__ import annotations

from .models import Document, Identity
from .service import RagService
from .store import Store

TENANT_ALPHA = "fixture-tenant-alpha"
TENANT_BETA = "fixture-tenant-beta"

GROUP_SUPPORT = "fixture-group-support"
GROUP_BILLING = "fixture-group-billing"
GROUP_FINANCE = "fixture-group-finance"

ALICE = Identity(TENANT_ALPHA, "fixture-user-alice",
                 (GROUP_SUPPORT, GROUP_BILLING))
BOB = Identity(TENANT_ALPHA, "fixture-user-bob", (GROUP_SUPPORT,))
DAVE = Identity(TENANT_ALPHA, "fixture-user-dave", ())
CAROL = Identity(TENANT_BETA, "fixture-user-carol", (GROUP_FINANCE,))

SEED_DOCS = [
    Document(
        doc_id="doc-alpha-refund", tenant_id=TENANT_ALPHA,
        title="Refund Policy", acl_type="tenant", sensitivity="internal",
        content=("Alpha refund policy. Customers receive a full refund "
                 "within 30 days for annual plans. Refunds are processed "
                 "to the original payment method within five business "
                 "days. The alpha support team approves refund exceptions "
                 "for annual plan customers.")),
    Document(
        doc_id="doc-beta-refund", tenant_id=TENANT_BETA,
        title="Refund Policy", acl_type="tenant", sensitivity="internal",
        content=("Beta refund policy. Customers receive a partial refund "
                 "within 14 days for monthly plans only. Refunds are "
                 "credited as account balance and cannot be withdrawn. "
                 "The beta finance team reviews every refund request for "
                 "monthly plan customers.")),
    Document(
        doc_id="doc-alpha-billing", tenant_id=TENANT_ALPHA,
        title="Billing Escalations", acl_type="groups",
        acl_groups=(GROUP_BILLING,), sensitivity="confidential",
        content=("Billing escalation runbook. Invoice disputes above five "
                 "thousand dollars go to the billing group lead. Chargeback "
                 "evidence is gathered from the payment processor within "
                 "two business days.")),
    Document(
        doc_id="doc-alpha-support", tenant_id=TENANT_ALPHA,
        title="Support Playbook", acl_type="groups",
        acl_groups=(GROUP_SUPPORT,), sensitivity="internal",
        content=("Support playbook. Triage every ticket within one hour. "
                 "Escalate outages to the on-call engineer and post a "
                 "status update every thirty minutes until resolved.")),
    Document(
        doc_id="doc-alpha-executive", tenant_id=TENANT_ALPHA,
        title="Executive Briefing", acl_type="users",
        acl_users=("fixture-user-alice",), sensitivity="restricted",
        content=("Executive briefing. The board approved the harbor "
                 "acquisition review in a closed session. Merger terms "
                 "remain restricted until the public announcement.")),
    Document(
        doc_id="doc-beta-finance", tenant_id=TENANT_BETA,
        title="Finance Notes", acl_type="groups",
        acl_groups=(GROUP_FINANCE,), sensitivity="confidential",
        content=("Finance notes. Quarterly revenue recognition follows "
                 "the beta finance calendar. Accruals are reconciled by "
                 "the finance group before the close.")),
]


def seed_service(store: Store | None = None) -> RagService:
    store = store or Store()
    service = RagService(store)
    actors = {TENANT_ALPHA: ALICE, TENANT_BETA: CAROL}
    for doc in SEED_DOCS:
        service.ingest(doc, actors[doc.tenant_id])
    return service
