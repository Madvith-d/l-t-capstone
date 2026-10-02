from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Conversation
from app.schemas.api import ConversationCreate, ConversationOut
from app.services.conversations import list_conversations

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationOut, status_code=201)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    conversation = Conversation(user_id=payload.user_id, title=payload.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("", response_model=list[ConversationOut])
def get_conversations(db: Session = Depends(get_db)):
    return list_conversations(db)


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
