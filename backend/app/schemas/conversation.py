from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: str
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: str
    role: str
    content: str
    mode: str | None
    provider: str | None
    created_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut]
