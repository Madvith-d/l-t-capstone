from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import ChatRequest, ChatResponse, Intent
from app.services.conversations import chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def send_message(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    try:
        conversation, result = chat(db, request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ChatResponse(
        conversation_id=conversation.id,
        intent=Intent(result["intent"]),
        answer=result["response"],
        sources=result.get("sources", []),
        confidence=result.get("confidence", 0),
        tool_results=result.get("tool_results", []),
    )
