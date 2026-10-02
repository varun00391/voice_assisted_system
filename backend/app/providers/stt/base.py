from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None
    duration_seconds: float


class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, *, max_duration_seconds: float) -> TranscriptionResult:
        """Transcribe encoded audio; raise AudioTooLongError if it exceeds the limit."""

    def warm_up(self) -> None:
        """Optionally load models ahead of the first request."""
