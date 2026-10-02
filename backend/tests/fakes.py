from app.core.errors import AudioTooLongError
from app.providers.llm.base import LLMProvider, LLMProviderError, LLMResult
from app.providers.stt.base import STTProvider, TranscriptionResult


class Truncated(str):
    """Scripted answer that stopped at max_tokens."""


class FakeLLMProvider(LLMProvider):
    """Returns scripted outcomes in order: a string answer, a Truncated answer or an LLMProviderError."""

    def __init__(self, name: str, outcomes: list[str | LLMProviderError] | None = None, model: str = "fake-model"):
        self.name = name
        self.model = model
        self._outcomes = list(outcomes or [])
        self.calls: list[list[dict[str, str]]] = []

    def queue(self, *outcomes: str | LLMProviderError) -> None:
        self._outcomes.extend(outcomes)

    async def generate(self, messages, model=None, temperature=0.2, max_tokens=None) -> LLMResult:
        self.calls.append(messages)
        outcome = self._outcomes.pop(0) if self._outcomes else f"answer from {self.name}"
        if isinstance(outcome, Exception):
            raise outcome
        return LLMResult(
            content=str(outcome),
            provider=self.name,
            model=model or self.model,
            truncated=isinstance(outcome, Truncated),
        )


def rate_limited() -> LLMProviderError:
    return LLMProviderError("429", error_type="rate_limited", retryable=True, status_code=429)


def server_error() -> LLMProviderError:
    return LLMProviderError("500", error_type="server_error", retryable=True, status_code=500)


def timeout() -> LLMProviderError:
    return LLMProviderError("timeout", error_type="timeout", retryable=True)


def incomplete() -> LLMProviderError:
    return LLMProviderError("max_tokens", error_type="incomplete", retryable=True)


def auth_error() -> LLMProviderError:
    return LLMProviderError("401", error_type="auth_error", retryable=False, status_code=401)


class FakeSTTProvider(STTProvider):
    def __init__(self, text: str = "Explain RAG architecture", duration_seconds: float = 3.0):
        self.text = text
        self.duration_seconds = duration_seconds
        self.calls = 0

    async def transcribe(self, audio: bytes, *, max_duration_seconds: float) -> TranscriptionResult:
        self.calls += 1
        if self.duration_seconds > max_duration_seconds:
            raise AudioTooLongError()
        return TranscriptionResult(text=self.text, language="en", duration_seconds=self.duration_seconds)
