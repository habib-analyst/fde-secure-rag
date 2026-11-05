"""SQLite storage: tenants' documents, chunks, and the append-only audit log."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from .chunking import chunk_document
from .models import Chunk, Document

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    acl_type TEXT NOT NULL,
    acl_groups TEXT NOT NULL DEFAULT '[]',
    acl_users TEXT NOT NULL DEFAULT '[]',
    sensitivity TEXT NOT NULL DEFAULT 'internal',
    created_by TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(doc_id),
    tenant_id TEXT NOT NULL,
    text TEXT NOT NULL,
    position INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,           -- ingest | query | deny
    actor_user TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    doc_ids TEXT NOT NULL DEFAULT '[]',
    denied_doc_ids TEXT NOT NULL DEFAULT '[]',
    result_count INTEGER NOT NULL DEFAULT 0,
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # -- documents / chunks -------------------------------------------------
    def add_document(self, doc: Document) -> list[Chunk]:
        doc.validate()
        with self.conn:
            self.conn.execute(
                "INSERT INTO documents (doc_id, tenant_id, title, content,"
                " acl_type, acl_groups, acl_users, sensitivity, created_by)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (doc.doc_id, doc.tenant_id, doc.title, doc.content,
                 doc.acl_type, json.dumps(list(doc.acl_groups)),
                 json.dumps(list(doc.acl_users)), doc.sensitivity,
                 doc.created_by))
            chunks = []
            for pos, (chunk_id, text) in enumerate(
                    chunk_document(doc.doc_id, doc.content)):
                self.conn.execute(
                    "INSERT INTO chunks (chunk_id, doc_id, tenant_id, text,"
                    " position) VALUES (?,?,?,?,?)",
                    (chunk_id, doc.doc_id, doc.tenant_id, text, pos))
                chunks.append(Chunk(chunk_id=chunk_id, doc_id=doc.doc_id,
                                    tenant_id=doc.tenant_id, text=text,
                                    position=pos))
        return chunks

    def _row_to_doc(self, row) -> Document:
        return Document(
            doc_id=row["doc_id"], tenant_id=row["tenant_id"],
            title=row["title"], content=row["content"],
            acl_type=row["acl_type"],
            acl_groups=tuple(json.loads(row["acl_groups"])),
            acl_users=tuple(json.loads(row["acl_users"])),
            sensitivity=row["sensitivity"], created_by=row["created_by"])

    def all_documents(self) -> list[Document]:
        rows = self.conn.execute("SELECT * FROM documents ORDER BY doc_id")
        return [self._row_to_doc(r) for r in rows]

    def get_document(self, doc_id: str) -> Document | None:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        return self._row_to_doc(row) if row else None

    def chunks_for_doc(self, doc_id: str) -> list[Chunk]:
        rows = self.conn.execute(
            "SELECT * FROM chunks WHERE doc_id=? ORDER BY position",
            (doc_id,))
        return [Chunk(chunk_id=r["chunk_id"], doc_id=r["doc_id"],
                      tenant_id=r["tenant_id"], text=r["text"],
                      position=r["position"]) for r in rows]

    def all_chunks(self) -> list[Chunk]:
        rows = self.conn.execute("SELECT * FROM chunks ORDER BY chunk_id")
        return [Chunk(chunk_id=r["chunk_id"], doc_id=r["doc_id"],
                      tenant_id=r["tenant_id"], text=r["text"],
                      position=r["position"]) for r in rows]

    # -- audit log (append-only: insert + read, no update/delete) -----------
    def log_audit(self, event_type: str, actor_user: str, tenant_id: str,
                  doc_ids=(), denied_doc_ids=(), result_count: int = 0,
                  detail: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO audit_log (event_type, actor_user, tenant_id,"
            " doc_ids, denied_doc_ids, result_count, detail, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (event_type, actor_user, tenant_id, json.dumps(list(doc_ids)),
             json.dumps(list(denied_doc_ids)), int(result_count), detail,
             _now()))
        self.conn.commit()
        return int(cur.lastrowid)

    def audit_entries(self, event_type: str | None = None) -> list[dict]:
        if event_type:
            rows = self.conn.execute(
                "SELECT * FROM audit_log WHERE event_type=? ORDER BY id",
                (event_type,))
        else:
            rows = self.conn.execute("SELECT * FROM audit_log ORDER BY id")
        out = []
        for r in rows:
            entry = dict(r)
            entry["doc_ids"] = json.loads(entry["doc_ids"])
            entry["denied_doc_ids"] = json.loads(entry["denied_doc_ids"])
            out.append(entry)
        return out
