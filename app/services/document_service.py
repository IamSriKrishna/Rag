import hashlib
from pathlib import Path
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.document import Document
from app.models.user import User
from app.repositories.document_repository import DocumentRepository


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DocumentRepository(db)
        self.upload_dir = Path(settings.upload_directory)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, file: UploadFile, user: User) -> Document:
        if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        content = await file.read(settings.max_upload_bytes + 1)
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413, detail="File exceeds the upload size limit"
            )
        if not content.startswith(b"%PDF"):
            raise HTTPException(
                status_code=400, detail="File does not appear to be a valid PDF"
            )
        file_hash = hashlib.sha256(content).hexdigest()
        existing = self.repo.get_by_hash(file_hash, user.tenant_id)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"This PDF is already registered as document {existing.id}",
            )
        safe_name = f"{file_hash}.pdf"
        path = self.upload_dir / safe_name
        path.write_bytes(content)
        document = Document(
            tenant_id=user.tenant_id,
            owner_id=user.id,
            filename=Path(file.filename).name[:255],
            file_path=str(path),
            file_hash=file_hash,
            file_size=len(content),
            status="queued",
        )
        try:
            return self.repo.create(document)
        except Exception:
            path.unlink(missing_ok=True)
            raise

    def get_owned(self, document_id: int, user: User) -> Document:
        document = self.repo.get_by_id_for_tenant(document_id, user.tenant_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return document

    def list_for_user_tenant(self, user: User) -> list[Document]:
        return self.repo.list_for_tenant(user.tenant_id)
