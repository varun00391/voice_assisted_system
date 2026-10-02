from typing import Annotated, Any

from pydantic import BeforeValidator, Field

from app.core.text import sanitize_text


def _clean(value: Any) -> Any:
    return sanitize_text(value) if isinstance(value, str) else value


def _clean_or_none(value: Any) -> Any:
    if isinstance(value, str):
        value = sanitize_text(value)
        return value or None
    return value


CleanStr = Annotated[str, BeforeValidator(_clean)]


def optional_clean_str(max_length: int) -> Any:
    """Sanitized optional text; blank strings become None."""
    return Annotated[Annotated[str, Field(max_length=max_length)] | None, BeforeValidator(_clean_or_none)]
