from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"

PLACEHOLDER_PREFIX = "replace-with"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT_ENV, ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_env: str = "development"
    app_version: str = "dev"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    api_access_key: SecretStr | None = None

    llm_provider_order: str = "groq,euron"
    llm_timeout_seconds: float = 30.0
    llm_temperature: float = 0.2
    llm_max_tokens: int = 4096
    llm_max_continuations: int = 2
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_cooldown_seconds: float = 60.0

    groq_api_key: SecretStr | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"
    groq_reasoning_format: str | None = None
    groq_reasoning_effort: str | None = None

    euron_api_key: SecretStr | None = None
    euron_base_url: str = "https://api.euron.one/api/v1/euri"
    euron_model: str = "gpt-4.1-nano"

    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str | None = None
    whisper_preload: bool = False
    stt_timeout_seconds: float = 120.0
    max_concurrent_transcriptions: int = 2

    max_audio_size_mb: float = 10.0
    max_audio_duration_seconds: float = 60.0

    database_url: str = "sqlite+aiosqlite:///./voice_assistant.db"

    max_history_messages: int = 12
    rate_limit_per_minute: int = 60
    local_user_id: str = "local-user"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def provider_order(self) -> list[str]:
        return [name.strip().lower() for name in self.llm_provider_order.split(",") if name.strip()]

    @property
    def max_audio_size_bytes(self) -> int:
        return int(self.max_audio_size_mb * 1024 * 1024)


def api_key_value(secret: SecretStr | None) -> str | None:
    if secret is None:
        return None
    value = secret.get_secret_value().strip()
    if not value or value.startswith(PLACEHOLDER_PREFIX):
        return None
    return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
