# Voice-Assisted Multi-LLM AI Assistant

Speak a question, pick an answer mode, get a text answer. Speech-to-text runs locally with faster-whisper; answers come from Groq with automatic fallback to Euron on rate limits and temporary failures. See `voice_assisted_system_plan.md` for the design.

## Run with Docker

```bash
cp .env.example .env      # or fill the provided empty .env
# set GROQ_API_KEY, EURON_API_KEY and POSTGRES_PASSWORD
docker compose up --build
```

- App: http://localhost:3000
- Backend API: http://localhost:8000 (docs at `/docs`)
- Health: http://localhost:8000/health

The first start downloads the Whisper model into the `whisper_models` volume.

## Run locally without Docker

Backend (Python 3.11+, uses SQLite when `DATABASE_URL` is blank):

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload
```

Frontend (Node 20+, proxies `/api` to `localhost:8000`):

```bash
cd frontend
npm install
npm run dev
```

Microphone access requires `localhost` or HTTPS.

## Tests

```bash
cd backend && .venv/bin/python -m pytest
cd frontend && npm test
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness |
| POST | `/api/v1/transcribe` | Audio (multipart `audio`) → transcript |
| POST | `/api/v1/chat` | Question + mode (+ optional preferred `provider`) → answer |
| POST | `/api/v1/voice/chat` | Audio + mode (+ optional `provider`) → transcript and answer |
| GET | `/api/v1/modes` | Available answer modes |
| GET/DELETE | `/api/v1/conversations[/{id}]` | Conversation history |
| GET/POST/PATCH/DELETE | `/api/v1/user/context` | User-provided persistent context |
| GET | `/api/v1/providers/health` | LLM provider circuit-breaker state |
