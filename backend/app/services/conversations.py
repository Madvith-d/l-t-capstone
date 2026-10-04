from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_user
from app.core.config import get_settings
from app.graph.workflow import AssistantWorkflow
from app.models import Conversation, Message, MessageRole
from app.schemas.api import ChatRequest


def get_or_create_conversation(db: Session, request: ChatRequest) -> Conversation:
    conversation = None
    if request.conversation_id:
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == request.user_id,
            )
        )
    if request.conversation_id and conversation is None:
        raise LookupError("Conversation not found")
    if conversation is None:
        ensure_user(db, request.user_id or "")
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
    if conversation.summary:
        history.insert(0, {"role": "user", "content": f"Earlier topics: {conversation.summary}"})
    db.add(
        Message(conversation_id=conversation.id, role=MessageRole.user, content=request.question)
    )
    try:
        result = AssistantWorkflow(db).invoke(
            {
                "user_id": request.user_id,
                "conversation_id": conversation.id,
                "question": request.question,
                "conversation_history": history,
                "filters": request.filters,
                "plan_id": request.plan_id,
                "plan_request": request.plan_request,
                "tool_calls": [],
                "tool_results": [],
                "sources": [],
                "confidence": 0,
                "errors": [],
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
        if len(history_messages) + 2 >= settings.conversation_history_limit:
            user_topics = [
                item["content"]
                for item in history
                if item["role"] == "user" and not item["content"].startswith("Earlier topics:")
            ][-4:]
            conversation.summary = " | ".join(user_topics + [request.question])[:1000]
        db.commit()
        db.refresh(conversation)
        return conversation, result
    except Exception:
        db.rollback()
        raise


def list_conversations(db: Session, user_id: str) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(100)
        ).all()
    )
