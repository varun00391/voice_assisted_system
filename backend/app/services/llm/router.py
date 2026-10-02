import logging
import time
from dataclasses import dataclass, field

from app.core.errors import (
    AllProvidersUnavailableError,
    LLMRequestRejectedError,
    NoProvidersConfiguredError,
    ProviderNotConfiguredError,
)
from app.providers.llm.base import LLMProvider, LLMProviderError, LLMResult
from app.services.llm.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

SUCCESS = "success"
SKIPPED_UNAVAILABLE = "skipped_unavailable"

CONTINUE_PROMPT = (
    "Your previous answer was cut off. Continue exactly where it stopped, mid-sentence if necessary. "
    "Do not repeat anything already written and do not add any preamble."
)


@dataclass(frozen=True)
class ProviderAttempt:
    provider: str
    model: str
    status: str
    latency_ms: int
    error_type: str | None = None


@dataclass(frozen=True)
class RouterResult:
    content: str
    provider: str
    model: str
    attempts: list[ProviderAttempt] = field(default_factory=list)
    truncated: bool = False

    @property
    def fallback_used(self) -> bool:
        return any(attempt.status != SUCCESS for attempt in self.attempts)


class LLMRouter:
    """Tries providers in priority order (optionally starting with a preferred one)
    and falls back to the others on retryable failures."""

    def __init__(
        self,
        providers: list[LLMProvider],
        *,
        failure_threshold: int,
        cooldown_seconds: float,
        temperature: float,
        max_tokens: int | None,
        max_continuations: int = 2,
        clock=time.monotonic,
    ):
        self._providers = providers
        self._breakers = {p.name: CircuitBreaker(failure_threshold, cooldown_seconds, clock) for p in providers}
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._max_continuations = max(0, max_continuations)

    @property
    def provider_names(self) -> list[str]:
        return [provider.name for provider in self._providers]

    async def generate(self, messages: list[dict[str, str]], preferred_provider: str | None = None) -> RouterResult:
        if not self._providers:
            raise NoProvidersConfiguredError()

        attempts: list[ProviderAttempt] = []
        for provider in self._ordered(preferred_provider):
            breaker = self._breakers[provider.name]
            if not breaker.allow_request():
                attempts.append(ProviderAttempt(provider.name, provider.model, SKIPPED_UNAVAILABLE, 0))
                logger.info("llm provider skipped: circuit open", extra={"provider": provider.name})
                continue

            started = time.perf_counter()
            try:
                result = await provider.generate(
                    messages, temperature=self._temperature, max_tokens=self._max_tokens
                )
            except LLMProviderError as exc:
                latency_ms = _elapsed_ms(started)
                attempts.append(ProviderAttempt(provider.name, provider.model, exc.error_type, latency_ms, exc.error_type))
                logger.warning(
                    "llm provider attempt failed",
                    extra={
                        "provider": provider.name,
                        "error_type": exc.error_type,
                        "status_code": exc.status_code,
                        "retryable": exc.retryable,
                        "latency_ms": latency_ms,
                        "detail": str(exc),
                    },
                )
                if not exc.retryable:
                    raise LLMRequestRejectedError(attempts=attempts) from exc
                breaker.record_failure()
                continue

            breaker.record_success()
            content, truncated, continuations = await self._continue_if_truncated(provider, messages, result)
            latency_ms = _elapsed_ms(started)
            attempts.append(ProviderAttempt(provider.name, result.model, SUCCESS, latency_ms))
            logger.info(
                "llm completed",
                extra={"provider": provider.name, "model": result.model, "latency_ms": latency_ms,
                       "fallback_used": len(attempts) > 1, "continuations": continuations,
                       "truncated": truncated},
            )
            return RouterResult(
                content=content,
                provider=provider.name,
                model=result.model,
                attempts=attempts,
                truncated=truncated,
            )

        logger.error("all llm providers failed", extra={"attempts": [a.status for a in attempts]})
        raise AllProvidersUnavailableError(attempts=attempts)

    async def _continue_if_truncated(
        self, provider: LLMProvider, messages: list[dict[str, str]], result: LLMResult
    ) -> tuple[str, bool, int]:
        """Ask the same provider to finish an answer that stopped at max_tokens."""
        content, truncated, rounds = result.content, result.truncated, 0
        while truncated and rounds < self._max_continuations:
            rounds += 1
            try:
                more = await provider.generate(
                    [*messages, {"role": "assistant", "content": content}, {"role": "user", "content": CONTINUE_PROMPT}],
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                )
            except LLMProviderError as exc:
                logger.warning(
                    "llm continuation failed; returning partial answer",
                    extra={"provider": provider.name, "error_type": exc.error_type},
                )
                break
            content += more.content
            truncated = more.truncated
        return content.strip(), truncated, rounds

    def _ordered(self, preferred_provider: str | None) -> list[LLMProvider]:
        if preferred_provider is None:
            return self._providers
        if preferred_provider not in self._breakers:
            raise ProviderNotConfiguredError(
                f"The AI provider '{preferred_provider}' is not configured. "
                f"Available: {', '.join(self.provider_names)}."
            )
        return sorted(self._providers, key=lambda provider: provider.name != preferred_provider)

    def health(self) -> list[dict]:
        return [
            {
                "provider": provider.name,
                "model": provider.model,
                "state": self._breakers[provider.name].state.value,
                "consecutive_failures": self._breakers[provider.name].consecutive_failures,
            }
            for provider in self._providers
        ]


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
