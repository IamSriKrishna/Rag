from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.document import Document


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id_for_tenant(self, document_id: int, tenant_id: int) -> Document | None:
        return self.db.scalar(
            select(Document).where(
                Document.id == document_id, Document.tenant_id == tenant_id
            )
        )

    def get_by_hash(self, file_hash: str, tenant_id: int) -> Document | None:
        return self.db.scalar(
            select(Document).where(
                Document.file_hash == file_hash, Document.tenant_id == tenant_id
            )
        )

    def list_for_tenant(self, tenant_id: int) -> list[Document]:
        return list(
            self.db.scalars(
                select(Document)
                .where(Document.tenant_id == tenant_id)
                .order_by(Document.created_at.desc())
            )
        )

    def create(self, document: Document) -> Document:
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def save(self, document: Document) -> Document:
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete(self, document: Document) -> None:
        self.db.delete(document)
        self.db.commit()
