from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.metrics import CACHE_HITS, CACHE_MISSES
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.rag import RAGResponse, SourceResponse
from app.services.cache_service import CacheService
from app.services.rag_service import RAGService


class RAGApplicationService:
    def __init__(self, db: Session, rag: RAGService, cache: CacheService):
        self.db = db
        self.rag = rag
        self.cache = cache
        self.documents = DocumentRepository(db)
        self.conversations = ConversationRepository(db)

    def ask(
        self,
        user: User,
        document_id: int,
        question: str,
        conversation_id: int | None = None,
    ) -> RAGResponse:
        document = self.documents.get_by_id_for_tenant(document_id, user.tenant_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        if document.status != "indexed":
            raise HTTPException(
                status_code=409, detail="Document is not ready for questions"
            )
        if conversation_id is not None:
            conversation = self.conversations.get_for_user(
                conversation_id, user.id, user.tenant_id
            )
            if conversation is None or conversation.document_id != document_id:
                raise HTTPException(status_code=404, detail="Conversation not found")
            history = self.conversations.get_messages(conversation.id)
        else:
            from app.models.conversation import Conversation

            conversation = self.conversations.create(
                Conversation(
                    tenant_id=user.tenant_id,
                    user_id=user.id,
                    document_id=document_id,
                    title=question[:70] or "New Conversation",
                )
            )
            history = []
        payload = {
            "tenant_id": user.tenant_id,
            "user_id": user.id,
            "document_id": document.id,
            "document_version": document.file_hash,
            "question": question.strip().lower(),
            "model": settings.ollama_chat_model,
            "prompt_version": settings.prompt_version,
        }
        cached = self.cache.get(payload) if not history else None
        if cached is not None:
            CACHE_HITS.inc()
            answer = cached["answer"]
            sources = [SourceResponse(**item) for item in cached["sources"]]
            was_cached = True
        else:
            CACHE_MISSES.inc()
            answer, sources = self.rag.answer(
                question,
                document.id,
                user.tenant_id,
                document.filename,
                history=history,
            )
            was_cached = False
            if not history:
                self.cache.set(
                    payload,
                    {"answer": answer, "sources": [s.model_dump() for s in sources]},
                )
        self.conversations.add_message(conversation.id, "user", question)
        self.conversations.add_message(conversation.id, "assistant", answer)
        return RAGResponse(
            answer=answer,
            sources=sources,
            conversation_id=conversation.id,
            cached=was_cached,
        )
