from datetime import datetime

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    title: str = Field(default="新对话", max_length=200)


class ChatSessionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ChatSessionOut(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    session_id: int
    role: str = Field(max_length=20)
    content: str


class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
