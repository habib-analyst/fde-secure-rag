# Launch Note — fde-secure-rag

20-point pre-launch checklist. Every item PASS or N/A with a reason.

1. **Tests green** — PASS: 40/40 passing with `python3 -m pytest tests/ -q` on Python 3.12.
2. **No secrets in code or fixtures** — PASS: no credentials anywhere; all identities and ids are synthetic `fixture-*` values.
3. **No real personal data** — PASS: the entire corpus is invented synthetic documents for two fictional tenants.
4. **No payment / paid services** — PASS: $0 stack; local SQLite, local TF-IDF, no external APIs, no LLM calls.
5. **Cross-tenant isolation tested** — PASS: exact-match cross-tenant queries in both directions return zero foreign chunks (tests/test_permissions.py).
6. **Filter-before-rank verified** — PASS: permitted-chunk scores are unchanged after a query-stuffed foreign document is ingested (tests/test_retrieval.py).
7. **ACL allow/deny tested** — PASS: group ACL and user ACL each have allow and deny tests, including same-tenant denial.
8. **Denied ids never leak** — PASS: tests assert denied doc ids are present in the audit log and absent from response results and answers.
9. **Citation integrity** — PASS: verifier accepts composed answers and rejects tampered citations pointing at another tenant's chunk.
10. **Audit completeness** — PASS: tests confirm an entry for every ingest and every query, plus deny entries at permission boundaries.
11. **Input validation** — PASS: 8 parametrized invalid-ACL/empty-field ingest cases rejected; API returns 422; failed ingests store nothing.
12. **Deterministic behaviour** — PASS: fixed-window chunking pinned by tests; identical inputs give identical chunks, ids, and rankings.
13. **README accuracy** — PASS: every number in the README (40 tests, 0 leaked chunks, top score 0.5943) was measured on the shipped code.
14. **Scope honesty** — PASS: README states plainly that answers are extractive, auth is fixture headers, and scale is local.
15. **No internal process language in public files** — PASS: README describes the system only; this launch note is the sole process document.
16. **Dependencies pinned loosely and free** — PASS: fastapi, pydantic, uvicorn; scikit-learn optional with a stdlib TF-IDF fallback (requirements.txt).
17. **Error handling fails closed** — PASS: unknown ACL types deny by default; citation verification failure raises instead of returning an answer.
18. **Health endpoint** — PASS: `GET /health` returns `{"status": "ok"}`, covered by a test.
19. **Clean file set** — PASS: package, tests, README, launch note, pyproject, requirements only; caches excluded from any distribution.
20. **Licence / attribution issues** — N/A: no third-party data, code, or assets are bundled; all content is original and synthetic.

Verdict: ready to publish.
