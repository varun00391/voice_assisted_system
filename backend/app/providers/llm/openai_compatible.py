from typing import Any

import httpx

from app.providers.llm.base import LLMProvider, LLMProviderError, LLMResult
from app.providers.llm.reasoning import strip_reasoning


class OpenAICompatibleProvider(LLMProvider):
    """Chat-completions client for providers exposing the OpenAI wire format."""

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.AsyncClient,
        timeout_seconds: float,
        extra_body: dict[str, Any] | None = None,
    ):
        self.name = name
        self.model = model
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._client = client
        self._timeout = timeout_seconds
        self._extra_body = extra_body or {}

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResult:
        model_name = model or self.model
        payload: dict = {"model": model_name, "messages": messages, "temperature": temperature, **self._extra_body}
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            response = await self._client.post(
                self._url,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise LLMProviderError(f"{self.name} timed out", error_type="timeout", retryable=True) from exc
        except httpx.TransportError as exc:
            raise LLMProviderError(
                f"{self.name} connection failed: {type(exc).__name__}", error_type="connection_error", retryable=True
            ) from exc

        self._raise_for_status(response)

        try:
            choice = response.json()["choices"][0]
            raw_content = choice["message"].get("content") or ""
            finish_reason = choice.get("finish_reason")
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            raise LLMProviderError(
                f"{self.name} returned an unexpected response body", error_type="invalid_response", retryable=True
            ) from exc
        if not isinstance(raw_content, str):
            raise LLMProviderError(f"{self.name} returned non-text content", error_type="invalid_response", retryable=True)

        content, stopped_while_reasoning = strip_reasoning(raw_content)
        truncated = finish_reason == "length" or stopped_while_reasoning
        if not content.strip():
            if truncated:
                raise LLMProviderError(
                    f"{self.name} reached max_tokens before producing an answer",
                    error_type="incomplete",
                    retryable=True,
                )
            raise LLMProviderError(f"{self.name} returned an empty answer", error_type="invalid_response", retryable=True)

        # Keep trailing whitespace on truncated output so a continuation can be appended verbatim.
        content = content.lstrip() if truncated else content.strip()
        return LLMResult(content=content, provider=self.name, model=model_name, truncated=truncated)

    def _raise_for_status(self, response: httpx.Response) -> None:
        status = response.status_code
        if status < 400:
            return
        detail = f"{self.name} returned HTTP {status}: {response.text[:300]}"
        if status == 429:
            raise LLMProviderError(detail, error_type="rate_limited", retryable=True, status_code=status)
        if status == 408 or status >= 500:
            raise LLMProviderError(detail, error_type="server_error", retryable=True, status_code=status)
        if status in (401, 403):
            raise LLMProviderError(detail, error_type="auth_error", retryable=False, status_code=status)
        raise LLMProviderError(detail, error_type="invalid_request", retryable=False, status_code=status)
