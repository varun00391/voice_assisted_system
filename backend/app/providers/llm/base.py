from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResult:
    content: str
    provider: str
    model: str
    truncated: bool = False


class LLMProviderError(Exception):
    """Provider failure classified for the router.

    `retryable` failures (rate limits, timeouts, 5xx, connection errors) trigger fallback;
    non-retryable failures (bad key, bad request) are surfaced instead.
    """

    def __init__(self, message: str, *, error_type: str, retryable: bool, status_code: int | None = None):
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable
        self.status_code = status_code


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResult: ...
