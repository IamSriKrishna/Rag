from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message


class ConversationRepository:
    def __int__(self, db: Session):
        self.db = db

    def get_for_user(
        self, conversation_id: int, user_id: int, tenant_id: int
    ) -> Conversation | None:

        return self.db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.tenant_id == tenant_id,
            )
        )

    def create(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    def add_message(self, conversation_id: int, role: str, content: str) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )

        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        return message

    def get_messages(self, conversation_id: int) -> list[Message]:
        return list(
            self.db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.id)
            )
        )
