import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class Citation(BaseModel):
    text: str
    page_number: int
    filename: str

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations: Optional[List[Citation]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
