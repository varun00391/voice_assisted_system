from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import CleanStr, optional_clean_str
from app.services.modes.config import ANSWER_MODES, DEFAULT_MODE

MAX_MESSAGE_LENGTH = 4000
MAX_CUSTOM_INSTRUCTIONS_LENGTH = 2000


def validate_mode(value: str) -> str:
    value = value.strip().lower()
    if value not in ANSWER_MODES:
        raise ValueError(f"Unknown mode. Valid modes: {', '.join(ANSWER_MODES)}")
    return value


def normalize_provider(value: str | None) -> str | None:
    """None, blank or "auto" means use the configured priority order."""
    if value is None:
        return None
    value = value.strip().lower()
    return None if value in ("", "auto") else value


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=36)
    message: Annotated[CleanStr, Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)]
    mode: str = DEFAULT_MODE
    provider: Annotated[str | None, Field(max_length=32)] = None
    custom_instructions: optional_clean_str(MAX_CUSTOM_INSTRUCTIONS_LENGTH) = None

    _validate_mode = field_validator("mode")(validate_mode)
    _normalize_provider = field_validator("provider")(normalize_provider)


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    mode: str
    provider: str
    fallback_used: bool
    truncated: bool
