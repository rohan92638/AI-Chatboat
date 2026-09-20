from sqlalchemy.orm import Session

from app.database.models import Conversation
from app.repositories.conversation_repository import (
    ConversationRepository,
)


class MemoryService:

    def __init__(self):
        self.repository = ConversationRepository()

    def get_or_create_conversation(
        self,
        db: Session,
        conversation_id: str,
    ):
        return self.repository.get_or_create(
            db,
            conversation_id,
        )

    def get_history(
        self,
        db: Session,
        conversation: Conversation,
        limit: int,
    ):
        return self.repository.get_messages(
            db,
            conversation,
            limit=limit,
        )

    def save_user_message(
        self,
        db: Session,
        conversation: Conversation,
        content: str,
    ):
        return self.repository.save_message(
            db,
            conversation,
            "user",
            content,
        )

    def save_assistant_message(
        self,
        db: Session,
        conversation: Conversation,
        content: str,
    ):
        return self.repository.save_message(
            db,
            conversation,
            "assistant",
            content,
        )