"""Core service: ingestion, permission-filtered retrieval, answers, audit.

Query path, in order:
1. Resolve the caller's permitted documents with the ACL predicate.
2. Audit-only denied detection: non-permitted documents whose text shares
   a query token are recorded as denied in the audit log. Their ids never
   enter the response, and they never touch ranking.
3. Build the TF-IDF retriever from permitted chunks ONLY (filter before
   rank — IDF is computed over the permitted corpus alone).
4. Rank, compose an extractive answer, and verify its citations against
   the retrieved set before returning anything.
5. Write the query audit entry (and a deny entry when step 2 found any).
"""
from __future__ import annotations

from .citations import assert_citations_valid, compose_answer
from .models import Document, Identity, IngestValidationError, can_access
from .retrieval import TfidfRetriever, tokenize
from .store import Store


class RagService:
    def __init__(self, store: Store):
        self.store = store

    # -- ingestion -----------------------------------------------------------
    def ingest(self, doc: Document, actor: Identity) -> dict:
        if doc.tenant_id != actor.tenant_id:
            raise IngestValidationError(
                "cannot ingest a document into another tenant")
        doc.created_by = actor.user_id
        chunks = self.store.add_document(doc)  # validates ACL metadata
        self.store.log_audit(
            "ingest", actor_user=actor.user_id, tenant_id=actor.tenant_id,
            doc_ids=[doc.doc_id], result_count=len(chunks),
            detail=f"chunks={len(chunks)} acl_type={doc.acl_type}")
        return {"doc_id": doc.doc_id, "tenant_id": doc.tenant_id,
                "chunk_ids": [c.chunk_id for c in chunks],
                "chunk_count": len(chunks)}

    # -- query ---------------------------------------------------------------
    def query(self, identity: Identity, query_text: str,
              top_k: int = 3) -> dict:
        if not query_text or not query_text.strip():
            raise IngestValidationError("query text is required")
        top_k = max(1, min(int(top_k), 20))

        docs = self.store.all_documents()
        doc_by_id = {d.doc_id: d for d in docs}
        permitted_doc_ids = {
            d.doc_id for d in docs if can_access(d, identity)}
        chunks = self.store.all_chunks()
        permitted_chunks = [c for c in chunks if c.doc_id in permitted_doc_ids]

        # Audit-only denied detection (ids go to the audit log, never out).
        query_tokens = set(tokenize(query_text))
        denied_doc_ids = sorted({
            c.doc_id for c in chunks
            if c.doc_id not in permitted_doc_ids
            and query_tokens & set(tokenize(c.text))
        })

        # Filter BEFORE rank: the retriever only ever sees permitted chunks.
        retriever = TfidfRetriever(permitted_chunks)
        results = retriever.search(query_text, top_k=top_k)

        result_payload = [{
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "title": doc_by_id[chunk.doc_id].title,
            "text": chunk.text,
            "score": round(float(score), 6),
        } for chunk, score in results]
        citations = [r["chunk_id"] for r in result_payload]
        answer = compose_answer(results)
        if results:
            # Fail closed: never return an answer whose citations are not
            # all in the retrieved permitted set.
            assert_citations_valid(answer, citations)

        self.store.log_audit(
            "query", actor_user=identity.user_id,
            tenant_id=identity.tenant_id,
            doc_ids=sorted({r["doc_id"] for r in result_payload}),
            denied_doc_ids=denied_doc_ids,
            result_count=len(result_payload),
            detail=f"top_k={top_k}")
        if denied_doc_ids:
            self.store.log_audit(
                "deny", actor_user=identity.user_id,
                tenant_id=identity.tenant_id,
                doc_ids=[], denied_doc_ids=denied_doc_ids,
                result_count=0,
                detail="query matched documents outside caller permissions")

        return {
            "query": query_text,
            "tenant_id": identity.tenant_id,
            "results": result_payload,
            "citations": citations,
            "answer": answer,
        }

    # -- audit ----------------------------------------------------------------
    def audit_log(self, event_type: str | None = None) -> list[dict]:
        return self.store.audit_entries(event_type)
