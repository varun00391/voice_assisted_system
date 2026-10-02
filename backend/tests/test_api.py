import asyncio

from sqlalchemy import select

from app.models.database import create_database
from app.models.entities import LLMRequestLog
from tests.fakes import Truncated, auth_error, rate_limited, server_error

AUDIO = ("question.webm", b"fake-audio-bytes", "audio/webm;codecs=opus")


def fetch_logs(settings) -> list[LLMRequestLog]:
    async def _fetch():
        engine, sessionmaker = create_database(settings.database_url)
        async with sessionmaker() as session:
            rows = list(await session.scalars(select(LLMRequestLog).order_by(LLMRequestLog.id)))
        await engine.dispose()
        return rows

    return asyncio.run(_fetch())


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert response.headers["X-Request-ID"]


def test_modes(client):
    body = client.get("/api/v1/modes").json()
    assert body["default"] == "learning"
    assert "interview" in [mode["key"] for mode in body["modes"]]


def test_chat_creates_conversation_and_persists_messages(client, groq):
    groq.queue("RAG stands for retrieval-augmented generation.")
    response = client.post("/api/v1/chat", json={"message": "Explain RAG architecture", "mode": "interview"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "RAG stands for retrieval-augmented generation."
    assert body["provider"] == "groq"
    assert body["fallback_used"] is False

    conversations = client.get("/api/v1/conversations").json()
    assert [c["conversation_id"] for c in conversations] == [body["conversation_id"]]
    assert conversations[0]["title"] == "Explain RAG architecture"

    detail = client.get(f"/api/v1/conversations/{body['conversation_id']}").json()
    assert [(m["role"], m["content"]) for m in detail["messages"]] == [
        ("user", "Explain RAG architecture"),
        ("assistant", "RAG stands for retrieval-augmented generation."),
    ]


def test_truncated_answer_is_completed_and_stored_whole(client, groq):
    groq.queue(Truncated("First half, "), "second half.")
    body = client.post("/api/v1/chat", json={"message": "long question"}).json()

    assert body["answer"] == "First half, second half."
    assert body["truncated"] is False
    detail = client.get(f"/api/v1/conversations/{body['conversation_id']}").json()
    assert detail["messages"][-1]["content"] == "First half, second half."


def test_follow_up_question_includes_history(client, groq):
    first = client.post("/api/v1/chat", json={"message": "What is RAG?"}).json()
    client.post(
        "/api/v1/chat", json={"message": "Why do we need embeddings?", "conversation_id": first["conversation_id"]}
    )

    sent = groq.calls[-1]
    assert [m["role"] for m in sent] == ["system", "user", "assistant", "user"]
    assert sent[1]["content"] == "What is RAG?"


def test_chat_falls_back_and_logs_attempts(client, settings, groq, euron):
    groq.queue(rate_limited())
    euron.queue("fallback answer")
    body = client.post("/api/v1/chat", json={"message": "hello"}).json()

    assert body["provider"] == "euron"
    assert body["fallback_used"] is True
    logs = fetch_logs(settings)
    assert [(log.provider, log.status) for log in logs] == [("groq", "rate_limited"), ("euron", "success")]
    assert logs[0].request_id == logs[1].request_id
    assert logs[0].conversation_id == body["conversation_id"]


def test_selected_euron_is_used_first(client, groq, euron):
    euron.queue("euron answer")
    body = client.post("/api/v1/chat", json={"message": "hello", "provider": "euron"}).json()

    assert body["provider"] == "euron"
    assert body["fallback_used"] is False
    assert groq.calls == []


def test_selected_euron_rate_limited_falls_back_to_groq(client, groq, euron):
    euron.queue(rate_limited())
    groq.queue("groq answer")
    body = client.post("/api/v1/chat", json={"message": "hello", "provider": "euron"}).json()

    assert body["provider"] == "groq"
    assert body["fallback_used"] is True


def test_auto_provider_uses_configured_order(client, groq, euron):
    body = client.post("/api/v1/chat", json={"message": "hello", "provider": "auto"}).json()
    assert body["provider"] == "groq"
    assert euron.calls == []


def test_unknown_provider_returns_400(client):
    response = client.post("/api/v1/chat", json={"message": "hello", "provider": "openai"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "provider_not_configured"


def test_voice_chat_honours_selected_provider(client, groq, euron):
    response = client.post("/api/v1/voice/chat", files={"audio": AUDIO}, data={"provider": "euron"})
    assert response.json()["provider"] == "euron"
    assert groq.calls == []


def test_all_providers_failing_returns_friendly_503_without_creating_conversation(client, settings, groq, euron):
    groq.queue(rate_limited())
    euron.queue(server_error())
    response = client.post("/api/v1/chat", json={"message": "hello"})

    assert response.status_code == 503
    assert response.json()["error"]["message"] == (
        "The AI providers are temporarily unavailable. Please try again shortly."
    )
    assert client.get("/api/v1/conversations").json() == []
    assert len(fetch_logs(settings)) == 2


def test_non_retryable_provider_error_is_surfaced(client, groq, euron):
    groq.queue(auth_error())
    response = client.post("/api/v1/chat", json={"message": "hello"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "llm_request_rejected"
    assert euron.calls == []
    assert "401" not in response.text


def test_chat_validation(client):
    assert client.post("/api/v1/chat", json={"message": "   "}).status_code == 422
    response = client.post("/api/v1/chat", json={"message": "hi", "mode": "poetry"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_unknown_conversation_returns_404(client):
    response = client.post("/api/v1/chat", json={"message": "hi", "conversation_id": "missing"})
    assert response.status_code == 404


def test_delete_conversation(client):
    conversation_id = client.post("/api/v1/chat", json={"message": "hi"}).json()["conversation_id"]
    assert client.delete(f"/api/v1/conversations/{conversation_id}").status_code == 204
    assert client.get(f"/api/v1/conversations/{conversation_id}").status_code == 404


def test_user_context_crud_and_prompt_injection(client, groq):
    assert client.get("/api/v1/user/context").json()["skills"] == []

    saved = client.post(
        "/api/v1/user/context",
        json={"professional_background": "Data Scientist", "skills": ["Python", "RAG"], "interview_goals": "AI Architect"},
    ).json()
    assert saved["professional_background"] == "Data Scientist"

    patched = client.patch("/api/v1/user/context", json={"experience_years": 10}).json()
    assert patched["experience_years"] == 10
    assert patched["skills"] == ["Python", "RAG"]

    client.post("/api/v1/chat", json={"message": "How should I prepare for this interview?", "mode": "concise"})
    assert "Data Scientist" in groq.calls[-1][0]["content"]

    client.post("/api/v1/chat", json={"message": "What is a vector database?", "mode": "concise"})
    assert "Data Scientist" not in groq.calls[-1][0]["content"]

    assert client.delete("/api/v1/user/context").status_code == 204
    assert client.get("/api/v1/user/context").json()["professional_background"] is None


def test_user_context_rejects_unknown_fields(client):
    assert client.post("/api/v1/user/context", json={"password": "x"}).status_code == 422


def test_user_context_accepts_nulls_and_blank_strings(client):
    response = client.post("/api/v1/user/context", json={"name": None, "preferences": "  ", "skills": ["Go"]})
    assert response.status_code == 200
    assert response.json()["preferences"] is None


def test_custom_instructions_length_is_limited(client):
    response = client.post(
        "/api/v1/chat", json={"message": "hi", "mode": "custom", "custom_instructions": "x" * 2001}
    )
    assert response.status_code == 422


def test_transcribe(client, stt):
    response = client.post("/api/v1/transcribe", files={"audio": AUDIO})
    assert response.status_code == 200
    assert response.json()["text"] == "Explain RAG architecture"
    assert stt.calls == 1


def test_transcribe_rejects_unsupported_format(client, stt):
    response = client.post("/api/v1/transcribe", files={"audio": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 415
    assert stt.calls == 0


def test_transcribe_accepts_octet_stream_with_audio_extension(client):
    response = client.post("/api/v1/transcribe", files={"audio": ("clip.wav", b"data", "application/octet-stream")})
    assert response.status_code == 200


def test_transcribe_rejects_large_file(client, stt):
    response = client.post(
        "/api/v1/transcribe", files={"audio": ("big.webm", b"x" * (1024 * 1024 + 1), "audio/webm")}
    )
    assert response.status_code == 413
    assert stt.calls == 0


def test_transcribe_rejects_long_audio(client, stt):
    stt.duration_seconds = 120
    assert client.post("/api/v1/transcribe", files={"audio": AUDIO}).status_code == 400


def test_empty_transcript(client, stt):
    stt.text = "   "
    response = client.post("/api/v1/transcribe", files={"audio": AUDIO})
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "No speech was detected. Please try again."


def test_voice_chat(client, groq):
    groq.queue("RAG stands for...")
    response = client.post("/api/v1/voice/chat", files={"audio": AUDIO}, data={"mode": "interview"})

    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == "Explain RAG architecture"
    assert body["answer"] == "RAG stands for..."
    assert body["mode"] == "interview"


def test_rate_limit(settings, groq, euron, stt):
    from fastapi.testclient import TestClient

    from app.main import create_app

    settings.rate_limit_per_minute = 2
    with TestClient(create_app(settings, stt_provider=stt, llm_providers=[groq, euron])) as limited:
        assert limited.get("/api/v1/modes").status_code == 200
        assert limited.get("/api/v1/modes").status_code == 200
        response = limited.get("/api/v1/modes")
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "rate_limited"
        assert limited.get("/health").status_code == 200
