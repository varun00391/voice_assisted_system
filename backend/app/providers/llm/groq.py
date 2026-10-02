import httpx

from app.providers.llm.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.AsyncClient,
        timeout_seconds: float,
        reasoning_format: str | None = None,
        reasoning_effort: str | None = None,
    ):
        # Groq only accepts these parameters for reasoning models, so they are sent only when configured.
        extra_body = {}
        if reasoning_format:
            extra_body["reasoning_format"] = reasoning_format
        if reasoning_effort:
            extra_body["reasoning_effort"] = reasoning_effort
        super().__init__(
            name="groq",
            base_url=base_url,
            api_key=api_key,
            model=model,
            client=client,
            timeout_seconds=timeout_seconds,
            extra_body=extra_body,
        )
