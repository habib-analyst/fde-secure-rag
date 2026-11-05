# fde-secure-rag

A secure customer RAG (retrieval-augmented generation) system for a
multi-tenant SaaS. Documents are ingested with per-document access
control lists, retrieval only ever searches what the caller is allowed
to see, every answer cites the chunks it came from — and those
citations are verified — and every ingest, query, and denied-access
event lands in an append-only audit log.

Answers are extractive: they are composed verbatim from retrieved
chunks. There are no LLM calls.

## Security model

**Filter before rank.** Retrieval is a two-step process where the
order matters:

1. The caller's permitted documents are resolved with the ACL
   predicate (tenant boundary first, then tenant-wide / group / user
   ACL).
2. The TF-IDF retriever is built from *those chunks only*.

Corpus statistics (document frequencies, IDF) are computed over the
permitted corpus alone, so a filtered-out chunk cannot influence any
score — not even indirectly. A test proves this: adding a foreign
tenant document stuffed with the query's exact terms does not change
any permitted chunk's score.

**Per-document ACLs.** Each document carries an owner tenant, an ACL
type (`tenant`, `groups`, or `users`), and a sensitivity label
(`internal`, `confidential`, `restricted`). The tenant boundary is
absolute: no ACL can grant cross-tenant access. Invalid ACL metadata
(a groups ACL with no groups, an unknown ACL type or sensitivity
label, empty content) is rejected at ingestion with a validation
error, and nothing is stored.

**Verified citations.** Every answer lists its chunks with
`[chunk_id]` citations (stable ids of the form `doc_id#chunk_n`). An
independent verifier re-checks the final answer: if any citation
points at a chunk that was not in this caller's retrieved permitted
set, the answer is rejected instead of returned.

**Audit log, with a hard boundary.** Ingest, query, and deny events
are appended to a SQLite audit table with actor, tenant, document
ids, denied document ids, and result counts. When a query's terms
match documents the caller may not see, those document ids are
recorded in the audit log only — they never appear in the response,
in any field.

## Data model

```
tenant ──< documents (owner tenant, ACL, sensitivity)
              └──< chunks   (stable ids: doc_id#chunk_n)
audit_log (append-only: ingest | query | deny)
```

Chunking is deterministic: fixed 50-word windows with a 10-word
overlap. The same text always produces the same chunks with the same
ids, pinned by tests.

## Seeded corpus

The demo corpus is synthetic and deliberately adversarial: two
tenants (`fixture-tenant-alpha`, `fixture-tenant-beta`) each have a
"Refund Policy" document with overlapping vocabulary and different
terms — alpha offers a full refund within 30 days, beta a partial
refund within 14 days. A permission bug would be visible immediately.
The corpus also includes a group-restricted billing runbook, a
group-restricted support playbook, a user-restricted executive
briefing, and a beta finance note.

## Run it

```bash
pip install -r requirements.txt

# API with the seeded corpus (http://127.0.0.1:8000)
PYTHONPATH=src python3 -m fde_secure_rag.serve

# Tests
python3 -m pytest tests/ -q
```

Caller identity is supplied with headers (synthetic `fixture-*`
values in the demo and tests; a production deployment puts a real
auth layer in front and maps its principal onto the same identity):

```
X-Tenant-Id: fixture-tenant-alpha
X-User-Id:   fixture-user-alice
X-Groups:    fixture-group-support,fixture-group-billing
```

```bash
curl -s -X POST localhost:8000/query \
  -H 'X-Tenant-Id: fixture-tenant-alpha' \
  -H 'X-User-Id: fixture-user-alice' \
  -H 'X-Groups: fixture-group-support,fixture-group-billing' \
  -H 'Content-Type: application/json' \
  -d '{"query": "full refund within 30 days annual plans", "top_k": 3}'
```

Ingest with `POST /documents` (same headers; the document is created
in the caller's tenant), and read the audit trail with `GET /audit`
(optionally `?event_type=deny`).

Retrieval uses scikit-learn's `TfidfVectorizer` when it is importable
and a stdlib TF-IDF implementation with the same ranking semantics
otherwise.

## Measured results

- **40 tests, all passing** (`python3 -m pytest tests/ -q`).
- Cross-tenant leakage: an alpha caller issuing the beta refund
  document *word for word* as the query receives **0 beta chunks** —
  only their own tenant's permitted documents, in both directions.
- Group ACL: the billing runbook is returned to a billing-group
  member and withheld from a support-only user asking about its exact
  topic; the withheld document id appears in the audit log's denied
  list and nowhere in the response.
- User ACL: the executive briefing is returned only to the named
  user; other users in the same tenant get no trace of it.
- Filter-before-rank: permitted-chunk scores are byte-identical
  before and after a query-stuffed foreign document is ingested.
- Ranking sanity: "full refund within 30 days annual plans" ranks
  alpha's refund chunk first (score 0.5943 on the seeded corpus);
  beta's equivalent query ranks beta's refund chunk first.
- Citation verification: composed answers pass; an answer tampered
  to cite another tenant's chunk is rejected.
- Audit completeness: all 6 seeded ingests and every query write an
  entry; boundary-crossing queries additionally write a deny entry.

## Scope and honesty

- Answers are extractive chunk listings with citations, not generated
  prose. There is no LLM anywhere in the system.
- Authentication is fixture headers, not a real identity provider.
  The permission predicate is the real control; identity resolution
  is intentionally a thin, replaceable layer.
- Scale is local and small by design: SQLite storage, in-memory
  TF-IDF over the permitted chunk set, one process. The security
  properties (filter-before-rank, citation verification, audit
  boundary) are the point; the ranking is a small, honest lexical
  baseline.
- Synthetic data only. No real customer documents, no external
  services, no cost.
