"""FastAPI app for fde-secure-rag.

Caller identity comes from fixture auth headers (synthetic values in
tests and demos; a production deployment puts a real auth layer in
front and maps its principal onto the same Identity):

    X-Tenant-Id: fixture-tenant-alpha
    X-User-Id:   fixture-user-alice
    X-Groups:    fixture-group-support,fixture-group-billing
"""
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .models import Document, Identity, IngestValidationError
from .service import RagService
from .store import Store


class IngestRequest(BaseModel):
    doc_id: str
    title: str
    content: str
    acl_type: str = "tenant"
    acl_groups: list[str] = Field(default_factory=list)
    acl_users: list[str] = Field(default_factory=list)
    sensitivity: str = "internal"


class QueryRequest(BaseModel):
    query: str
    top_k: int = 3


def _identity(x_tenant_id: str, x_user_id: str, x_groups: str) -> Identity:
    groups = tuple(g.strip() for g in x_groups.split(",") if g.strip())
    try:
        return Identity(tenant_id=x_tenant_id, user_id=x_user_id, groups=groups)
    except IngestValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def create_app(service: RagService | None = None) -> FastAPI:
    service = service or RagService(Store())
    app = FastAPI(title="fde-secure-rag", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/documents", status_code=201)
    def ingest(body: IngestRequest,
               x_tenant_id: str = Header(...),
               x_user_id: str = Header(...),
               x_groups: str = Header("")):
        identity = _identity(x_tenant_id, x_user_id, x_groups)
        doc = Document(
            doc_id=body.doc_id, tenant_id=identity.tenant_id,
            title=body.title, content=body.content,
            acl_type=body.acl_type, acl_groups=tuple(body.acl_groups),
            acl_users=tuple(body.acl_users), sensitivity=body.sensitivity)
        try:
            return service.ingest(doc, identity)
        except IngestValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:  # duplicate doc_id etc.
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/query")
    def query(body: QueryRequest,
              x_tenant_id: str = Header(...),
              x_user_id: str = Header(...),
              x_groups: str = Header("")):
        identity = _identity(x_tenant_id, x_user_id, x_groups)
        try:
            return service.query(identity, body.query, top_k=body.top_k)
        except IngestValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/audit")
    def audit(event_type: str | None = None):
        return {"entries": service.audit_log(event_type)}

    return app


app = create_app()
