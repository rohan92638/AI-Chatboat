from sqlalchemy.orm import Session

from app.database.models import Conversation, Message


class ConversationRepository:

    def get_or_create(
        self,
        db: Session,
        conversation_id: str,
    ):
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.conversation_id
                == conversation_id
            )
            .first()
        )

        if conversation:
            return conversation

        conversation = Conversation(
            conversation_id=conversation_id
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        return conversation

    def get_messages(
        self,
        db: Session,
        conversation: Conversation,
        limit: int = 20,
    ):
        messages = (
            db.query(Message)
            .filter(
                Message.conversation_id
                == conversation.id
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )

        return list(reversed(messages))

    def save_message(
        self,
        db: Session,
        conversation: Conversation,
        role: str,
        content: str,
    ):
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        return message