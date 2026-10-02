import httpx

from app.providers.llm.openai_compatible import OpenAICompatibleProvider


class EuronProvider(OpenAICompatibleProvider):
    def __init__(self, *, base_url: str, api_key: str, model: str, client: httpx.AsyncClient, timeout_seconds: float):
        super().__init__(
            name="euron",
            base_url=base_url,
            api_key=api_key,
            model=model,
            client=client,
            timeout_seconds=timeout_seconds,
        )
