import pytest

from app.models.database import normalize_database_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "postgresql://user:p%40ss@ep-cool.ap-southeast-1.aws.neon.tech/app?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://user:p%40ss@ep-cool.ap-southeast-1.aws.neon.tech/app?ssl=require",
        ),
        (
            "postgres://user:pw@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
            "postgresql+asyncpg://user:pw@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
        ),
        (
            "postgresql+asyncpg://user:pw@postgres:5432/voice_assistant",
            "postgresql+asyncpg://user:pw@postgres:5432/voice_assistant",
        ),
        ("sqlite+aiosqlite:///./voice_assistant.db", "sqlite+aiosqlite:///./voice_assistant.db"),
    ],
)
def test_normalize_database_url(url, expected):
    assert normalize_database_url(url) == expected
