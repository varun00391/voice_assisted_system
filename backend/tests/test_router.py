import pytest

from app.core.errors import (
    AllProvidersUnavailableError,
    LLMRequestRejectedError,
    NoProvidersConfiguredError,
    ProviderNotConfiguredError,
)
from app.services.llm.circuit_breaker import CircuitBreaker, ProviderHealth
from app.services.llm.router import LLMRouter
from tests.fakes import FakeLLMProvider, Truncated, auth_error, incomplete, rate_limited, server_error, timeout

MESSAGES = [{"role": "user", "content": "hi"}]


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make_router(*providers, threshold=3, cooldown=60.0, clock=None) -> LLMRouter:
    return LLMRouter(
        list(providers),
        failure_threshold=threshold,
        cooldown_seconds=cooldown,
        temperature=0.2,
        max_tokens=256,
        clock=clock or FakeClock(),
    )


async def test_primary_success_does_not_call_fallback():
    groq, euron = FakeLLMProvider("groq", ["groq answer"]), FakeLLMProvider("euron")
    result = await make_router(groq, euron).generate(MESSAGES)

    assert result.content == "groq answer"
    assert result.provider == "groq"
    assert not result.fallback_used
    assert euron.calls == []


@pytest.mark.parametrize("failure", [rate_limited, server_error, timeout])
async def test_retryable_failure_falls_back(failure):
    groq, euron = FakeLLMProvider("groq", [failure()]), FakeLLMProvider("euron", ["euron answer"])
    result = await make_router(groq, euron).generate(MESSAGES)

    assert result.provider == "euron"
    assert result.fallback_used
    assert [a.status for a in result.attempts] == [failure().error_type, "success"]


async def test_non_retryable_failure_is_not_masked_by_fallback():
    groq, euron = FakeLLMProvider("groq", [auth_error()]), FakeLLMProvider("euron")
    with pytest.raises(LLMRequestRejectedError) as excinfo:
        await make_router(groq, euron).generate(MESSAGES)

    assert euron.calls == []
    assert excinfo.value.attempts[0].status == "auth_error"


async def test_all_providers_failing_raises_with_attempts():
    groq, euron = FakeLLMProvider("groq", [rate_limited()]), FakeLLMProvider("euron", [server_error()])
    with pytest.raises(AllProvidersUnavailableError) as excinfo:
        await make_router(groq, euron).generate(MESSAGES)

    assert [a.provider for a in excinfo.value.attempts] == ["groq", "euron"]


async def test_preferred_provider_is_tried_first():
    groq, euron = FakeLLMProvider("groq"), FakeLLMProvider("euron", ["euron answer"])
    result = await make_router(groq, euron).generate(MESSAGES, preferred_provider="euron")

    assert result.provider == "euron"
    assert not result.fallback_used
    assert groq.calls == []


async def test_preferred_provider_falls_back_to_the_others():
    groq, euron = FakeLLMProvider("groq", ["groq answer"]), FakeLLMProvider("euron", [rate_limited()])
    result = await make_router(groq, euron).generate(MESSAGES, preferred_provider="euron")

    assert result.provider == "groq"
    assert result.fallback_used
    assert [a.provider for a in result.attempts] == ["euron", "groq"]


async def test_unknown_preferred_provider_is_rejected():
    with pytest.raises(ProviderNotConfiguredError):
        await make_router(FakeLLMProvider("groq")).generate(MESSAGES, preferred_provider="openai")


async def test_truncated_answer_is_continued_on_same_provider():
    groq = FakeLLMProvider("groq", [Truncated("RAG has five "), "steps: ingest, chunk, embed, retrieve, generate."])
    euron = FakeLLMProvider("euron")
    result = await make_router(groq, euron).generate(MESSAGES)

    assert result.content == "RAG has five steps: ingest, chunk, embed, retrieve, generate."
    assert not result.truncated
    assert euron.calls == []
    continuation = groq.calls[1]
    assert continuation[-2] == {"role": "assistant", "content": "RAG has five "}
    assert continuation[-1]["role"] == "user"


async def test_continuation_stops_after_limit_and_flags_truncation():
    groq = FakeLLMProvider("groq", [Truncated("a "), Truncated("b "), Truncated("c "), "never requested"])
    router = LLMRouter(
        [groq], failure_threshold=3, cooldown_seconds=60, temperature=0.2, max_tokens=10, max_continuations=2
    )
    result = await router.generate(MESSAGES)

    assert result.content == "a b c"
    assert result.truncated
    assert len(groq.calls) == 3


async def test_failed_continuation_returns_partial_answer():
    groq = FakeLLMProvider("groq", [Truncated("partial answer "), server_error()])
    result = await make_router(groq).generate(MESSAGES)

    assert result.content == "partial answer"
    assert result.truncated


async def test_answer_lost_to_reasoning_falls_back():
    groq, euron = FakeLLMProvider("groq", [incomplete()]), FakeLLMProvider("euron", ["euron answer"])
    result = await make_router(groq, euron).generate(MESSAGES)

    assert result.provider == "euron"
    assert result.attempts[0].status == "incomplete"


async def test_no_providers_configured():
    with pytest.raises(NoProvidersConfiguredError):
        await make_router().generate(MESSAGES)


async def test_open_circuit_skips_provider_until_cooldown():
    clock = FakeClock()
    groq = FakeLLMProvider("groq", [rate_limited(), rate_limited()])
    euron = FakeLLMProvider("euron")
    router = make_router(groq, euron, threshold=2, cooldown=30, clock=clock)

    await router.generate(MESSAGES)
    await router.generate(MESSAGES)
    assert router.health()[0]["state"] == "unavailable"

    result = await router.generate(MESSAGES)
    assert len(groq.calls) == 2
    assert result.attempts[0].status == "skipped_unavailable"
    assert result.provider == "euron"
    assert result.fallback_used

    clock.now = 31
    result = await router.generate(MESSAGES)
    assert result.provider == "groq"
    assert router.health()[0]["state"] == "healthy"


def test_circuit_breaker_states():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=10, clock=clock)
    assert breaker.state is ProviderHealth.HEALTHY

    breaker.record_failure()
    assert breaker.state is ProviderHealth.DEGRADED
    assert breaker.allow_request()

    breaker.record_failure()
    assert breaker.state is ProviderHealth.UNAVAILABLE
    assert not breaker.allow_request()

    clock.now = 10
    assert breaker.allow_request()
    breaker.record_failure()
    assert not breaker.allow_request()

    clock.now = 20
    breaker.record_success()
    assert breaker.state is ProviderHealth.HEALTHY
