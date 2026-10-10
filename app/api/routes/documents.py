from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    File,
    status,
)
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService
from app.tasks.document_tasks import process_document_task

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await DocumentService(db).upload(file, current_user)
    background_tasks.add_task(
        process_document_task, request.app.state.rag_service, document.id
    )
    return document


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return DocumentRepository(db).list_for_tenant(current_user.tenant_id)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = DocumentRepository(db).get_by_id_for_tenant(
        document_id, current_user.tenant_id
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id}/status")
def document_status(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = DocumentRepository(db).get_by_id_for_tenant(
        document_id, current_user.tenant_id
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "document_id": document.id,
        "status": document.status,
        "pages": document.pages,
        "chunks": document.chunks,
    }


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = DocumentRepository(db)
    document = repo.get_by_id_for_tenant(document_id, current_user.tenant_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    request.app.state.rag_service.delete_document_vectors(
        document.id, current_user.tenant_id
    )
    from pathlib import Path

    file_path = Path(document.file_path)
    repo.delete(document)
    file_path.unlink(missing_ok=True)
    return None
