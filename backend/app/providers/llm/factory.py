import logging

import httpx

from app.config.settings import Settings, api_key_value
from app.providers.llm.base import LLMProvider
from app.providers.llm.euron import EuronProvider
from app.providers.llm.groq import GroqProvider

logger = logging.getLogger(__name__)


def build_llm_providers(settings: Settings, client: httpx.AsyncClient) -> list[LLMProvider]:
    """Build enabled providers in priority order (LLM_PROVIDER_ORDER), skipping ones without a key."""
    available = {
        "groq": (
            GroqProvider,
            settings.groq_api_key,
            settings.groq_base_url,
            settings.groq_model,
            {"reasoning_format": settings.groq_reasoning_format, "reasoning_effort": settings.groq_reasoning_effort},
        ),
        "euron": (EuronProvider, settings.euron_api_key, settings.euron_base_url, settings.euron_model, {}),
    }

    providers: list[LLMProvider] = []
    for name in settings.provider_order:
        if name not in available:
            logger.warning("unknown llm provider in LLM_PROVIDER_ORDER", extra={"provider": name})
            continue
        provider_cls, secret, base_url, model, options = available[name]
        api_key = api_key_value(secret)
        if api_key is None:
            logger.warning("llm provider disabled: api key not set", extra={"provider": name})
            continue
        providers.append(
            provider_cls(
                base_url=base_url,
                api_key=api_key,
                model=model,
                client=client,
                timeout_seconds=settings.llm_timeout_seconds,
                **options,
            )
        )

    logger.info("llm providers configured", extra={"providers": [p.name for p in providers]})
    return providers
