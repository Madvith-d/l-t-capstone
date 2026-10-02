from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.graph.workflow import AssistantWorkflow
from app.models import Conversation, Message, MessageRole
from app.schemas.api import ChatRequest


def get_or_create_conversation(db: Session, request: ChatRequest) -> Conversation:
    conversation = (
        db.get(Conversation, request.conversation_id) if request.conversation_id else None
    )
    if request.conversation_id and conversation is None:
        raise LookupError("Conversation not found")
    if conversation is None:
        conversation = Conversation(user_id=request.user_id, title=request.question[:80])
        db.add(conversation)
        db.flush()
    return conversation


def chat(db: Session, request: ChatRequest) -> tuple[Conversation, dict]:
    conversation = get_or_create_conversation(db, request)
    settings = get_settings()
    history_messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(settings.conversation_history_limit)
    ).all()
    history = [
        {"role": message.role.value, "content": message.content}
        for message in reversed(history_messages)
    ]
    db.add(
        Message(conversation_id=conversation.id, role=MessageRole.user, content=request.question)
    )
    result = AssistantWorkflow(db).invoke(
        {
            "user_id": request.user_id,
            "question": request.question,
            "conversation_history": history,
            "filters": request.filters,
            "tool_calls": [],
            "tool_results": [],
            "sources": [],
            "confidence": 0,
        }
    )
    db.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=result["response"],
            sources=result.get("sources", []),
        )
    )
    db.commit()
    db.refresh(conversation)
    return conversation, result


def list_conversations(db: Session) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc())
        ).all()
    )
