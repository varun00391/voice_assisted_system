import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.main import create_app
from tests.fakes import FakeLLMProvider, FakeSTTProvider


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        max_audio_size_mb=1,
        max_audio_duration_seconds=60,
        rate_limit_per_minute=1000,
        log_level="WARNING",
    )


@pytest.fixture
def groq() -> FakeLLMProvider:
    return FakeLLMProvider("groq")


@pytest.fixture
def euron() -> FakeLLMProvider:
    return FakeLLMProvider("euron")


@pytest.fixture
def stt() -> FakeSTTProvider:
    return FakeSTTProvider()


@pytest.fixture
def client(settings, groq, euron, stt):
    app = create_app(settings, stt_provider=stt, llm_providers=[groq, euron])
    with TestClient(app) as test_client:
        yield test_client
