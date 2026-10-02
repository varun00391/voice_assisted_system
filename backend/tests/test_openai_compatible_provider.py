import httpx
import pytest

from app.providers.llm.base import LLMProviderError
from app.providers.llm.groq import GroqProvider


def make_provider(handler) -> GroqProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return GroqProvider(
        base_url="https://llm.test/v1", api_key="secret", model="test-model", client=client, timeout_seconds=5
    )


async def test_successful_completion_sends_openai_payload():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = request.read()
        return httpx.Response(200, json={"choices": [{"message": {"content": "  hello  "}}]})

    result = await make_provider(handler).generate([{"role": "user", "content": "hi"}], max_tokens=50)

    assert result.content == "hello"
    assert result.provider == "groq"
    assert seen["url"] == "https://llm.test/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    assert b'"max_tokens":50' in seen["body"]


@pytest.mark.parametrize(
    ("status", "error_type", "retryable"),
    [
        (429, "rate_limited", True),
        (500, "server_error", True),
        (503, "server_error", True),
        (401, "auth_error", False),
        (400, "invalid_request", False),
        (404, "invalid_request", False),
    ],
)
async def test_http_errors_are_classified(status, error_type, retryable):
    provider = make_provider(lambda request: httpx.Response(status, json={"error": "x"}))
    with pytest.raises(LLMProviderError) as excinfo:
        await provider.generate([{"role": "user", "content": "hi"}])

    assert excinfo.value.error_type == error_type
    assert excinfo.value.retryable is retryable


async def test_timeout_is_retryable():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(LLMProviderError) as excinfo:
        await make_provider(handler).generate([{"role": "user", "content": "hi"}])
    assert excinfo.value.error_type == "timeout"
    assert excinfo.value.retryable


async def test_connection_error_is_retryable():
    def handler(request):
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(LLMProviderError) as excinfo:
        await make_provider(handler).generate([{"role": "user", "content": "hi"}])
    assert excinfo.value.error_type == "connection_error"


def completion(content, finish_reason="stop"):
    return lambda request: httpx.Response(
        200, json={"choices": [{"message": {"content": content}, "finish_reason": finish_reason}]}
    )


async def test_reasoning_block_is_removed_from_answer():
    result = await make_provider(completion("<think>Let me plan the answer.</think>\n\nRAG is retrieval.")).generate(
        [{"role": "user", "content": "hi"}]
    )
    assert result.content == "RAG is retrieval."
    assert not result.truncated


async def test_length_finish_reason_marks_answer_truncated():
    result = await make_provider(completion("RAG has five ", "length")).generate([{"role": "user", "content": "hi"}])
    assert result.truncated
    assert result.content == "RAG has five "


async def test_output_cut_off_while_reasoning_is_retryable_incomplete():
    provider = make_provider(completion("<think>Step one, step two and then", "length"))
    with pytest.raises(LLMProviderError) as excinfo:
        await provider.generate([{"role": "user", "content": "hi"}])
    assert excinfo.value.error_type == "incomplete"
    assert excinfo.value.retryable


async def test_groq_reasoning_options_are_sent_only_when_configured():
    bodies = []

    def handler(request):
        bodies.append(request.read())
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    common = dict(base_url="https://llm.test/v1", api_key="k", model="m", client=client, timeout_seconds=5)
    await GroqProvider(**common, reasoning_format="hidden", reasoning_effort="none").generate([])
    await GroqProvider(**common).generate([])

    assert b'"reasoning_format":"hidden"' in bodies[0] and b'"reasoning_effort":"none"' in bodies[0]
    assert b"reasoning" not in bodies[1]


async def test_empty_answer_is_retryable_invalid_response():
    provider = make_provider(lambda request: httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}))
    with pytest.raises(LLMProviderError) as excinfo:
        await provider.generate([{"role": "user", "content": "hi"}])
    assert excinfo.value.error_type == "invalid_response"
    assert excinfo.value.retryable
