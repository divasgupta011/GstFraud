# app/routers/chat.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.chat import ChatRequest, ChatResponse, ChatToolCall
from ..services.chat_service import handle_chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, db: Session = Depends(get_db)):
    result = handle_chat(payload.query, db=db)

    tool_call = None
    if result.get("tool_call"):
        tool_call = ChatToolCall(
            action=result["tool_call"]["action"],
            params=result["tool_call"]["params"],
        )

    return ChatResponse(
        answer=result["answer"],
        tool_call=tool_call,
        raw_tool_result=result.get("raw_tool_result"),
    )
