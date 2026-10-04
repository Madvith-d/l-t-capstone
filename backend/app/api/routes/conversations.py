from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import ensure_user, get_user_id
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Conversation
from app.schemas.api import ConversationCreate, ConversationOut, ConversationSummary
from app.services.conversations import list_conversations
from app.services.demo import ensure_demo_conversations

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationOut, status_code=201)
def create_conversation(
    payload: ConversationCreate,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    if payload.user_id and payload.user_id != user_id:
        raise HTTPException(status_code=403, detail="User identity does not match the request")
    ensure_user(db, user_id)
    conversation = Conversation(user_id=user_id, title=payload.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("", response_model=list[ConversationSummary])
def get_conversations(
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    if get_settings().demo_mode:
        ensure_demo_conversations(db, user_id)
        db.commit()
        return [
            conversation
            for conversation in list_conversations(db, user_id)
            if (conversation.summary or "").startswith("demo:seed:v3:")
        ]
    return list_conversations(db, user_id)


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    conversation = db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .options(selectinload(Conversation.messages))
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
