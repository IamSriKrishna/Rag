import logging
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


def process_document_task(rag_service, document_id: int):
    db: Session = SessionLocal()
    repo = DocumentRepository(db)
    document = None
    try:
        document = db.get(
            __import__("app.models.document", fromlist=["Document"]).Document,
            document_id,
        )
        if document is None:
            return
        document.status = "processing"
        db.commit()
        pages, chunks = rag_service.index_pdf(
            document.file_path, document.id, document.tenant_id
        )
        document.pages = pages
        document.chunks = chunks
        document.status = "indexed"
        db.commit()
        logger.info(
            "document_indexed document_id=%s tenant_id=%s pages=%s chunks=%s",
            document.id,
            document.tenant_id,
            pages,
            chunks,
        )
    except Exception:
        db.rollback()
        logger.exception("document_processing_failed document_id=%s", document_id)
        document = db.get(
            __import__("app.models.document", fromlist=["Document"]).Document,
            document_id,
        )
        if document is not None:
            document.status = "failed"
            db.commit()
    finally:
        db.close()
