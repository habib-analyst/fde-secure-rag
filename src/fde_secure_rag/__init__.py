"""fde-secure-rag: secure multi-tenant RAG with filter-before-rank
retrieval, verified citations, and a full audit log."""
from .citations import CitationError, compose_answer, verify_citations
from .models import Document, Identity, IngestValidationError, can_access
from .service import RagService
from .store import Store

__all__ = [
    "CitationError", "Document", "Identity", "IngestValidationError",
    "RagService", "Store", "can_access", "compose_answer",
    "verify_citations",
]
__version__ = "0.1.0"
