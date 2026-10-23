import json
import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.schemas.rag import RAGRequest, RAGResponse
from app.services.rag_application_service import RAGApplicationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/ask", response_model=RAGResponse)
def ask(
    payload: RAGRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = RAGApplicationService(
        db, request.app.state.rag_service, request.app.state.cache_service
    )
    return service.ask(
        current_user, payload.document_id, payload.question, payload.conversation_id
    )


@router.post("/ask/stream")
def ask_stream(
    payload: RAGRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = RAGApplicationService(
        db,
        request.app.state.rag_service,
        request.app.state.cache_service,
    )
    if payload.document_id is None:
        search_documents = application.documents.list_indexed_for_tenant(
            current_user.tenant_id
        )
        if not search_documents:
            raise HTTPException(
                status_code=409,
                detail="No indexed documents are available to search",
            )
        document = None
    else:
        document = application.documents.get_by_id_for_tenant(
            payload.document_id, current_user.tenant_id
        )
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        if document.status != "indexed":
            raise HTTPException(
                status_code=409, detail="Document is not ready for questions"
            )
        search_documents = [document]

    if payload.conversation_id is not None:
        conversation = application.conversations.get_for_user(
            payload.conversation_id, current_user.id, current_user.tenant_id
        )
        if conversation is None or conversation.document_id != payload.document_id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        history = application.conversations.get_messages(conversation.id)
    else:
        conversation = application.conversations.create(
            Conversation(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                document_id=payload.document_id,
                title=payload.question[:70],
            )
        )
        history = []

    scope_filename = document.filename if document is not None else None

    def generate():
        answer_parts: list[str] = []
        try:
            application.conversations.add_message(
                conversation.id, "user", payload.question
            )
            for token in request.app.state.rag_service.stream_answer(
                payload.question,
                payload.document_id,
                current_user.tenant_id,
                scope_filename,
                history=history,
            ):
                answer_parts.append(token)
                yield json.dumps(
                    {"type": "token", "content": token}, ensure_ascii=False
                ) + "\n"
            application.conversations.add_message(
                conversation.id, "assistant", "".join(answer_parts)
            )
            yield json.dumps(
                {
                    "type": "done",
                    "conversation_id": conversation.id,
                }
            ) + "\n"
        except Exception:
            logger.exception(
                "rag_stream_failed document_id=%s", payload.document_id
            )
            db.rollback()
            yield json.dumps(
                {"type": "error", "message": "Answer generation failed."}
            ) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
