from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_user_id
from app.db.session import get_db
from app.schemas.api import ChatRequest, ChatResponse, Intent
from app.services.conversations import chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def send_message(
    request: ChatRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> ChatResponse:
    if request.user_id and request.user_id != user_id:
        raise HTTPException(status_code=403, detail="User identity does not match the request")
    request.user_id = user_id
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
        graph_route=result.get("graph_route", []),
    )
