# app/schemas/chat.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ChatRequest(BaseModel):
    query: str


class ChatToolCall(BaseModel):
    action: str
    params: Dict[str, Any]


class ChatResponse(BaseModel):
    answer: str
    tool_call: Optional[ChatToolCall] = None
    raw_tool_result: Optional[Dict[str, Any]] = None
