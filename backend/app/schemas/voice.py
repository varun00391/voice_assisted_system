from pydantic import BaseModel


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None
    duration_seconds: float


class VoiceChatResponse(BaseModel):
    transcript: str
    conversation_id: str
    message_id: str
    answer: str
    mode: str
    provider: str
    fallback_used: bool
    truncated: bool
