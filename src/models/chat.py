# src/models/chat.py
from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    profile: Optional[dict] = None
