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
cd backend && .venv/bin/ruff check app tests && .venv/bin/python -m pytest
cd frontend && npm test
```

## Deploy to Azure (GitHub Actions)

Pushing to `main` runs the workflows in `.github/workflows/`:

- **Backend:** lint and test. The image is built with the Whisper model baked in, tagged with the commit SHA and pushed to Azure Container Registry. It is then deployed as a new Container Apps revision, and the workflow waits until `/health` reports that SHA.
- **Frontend:** test and build with `VITE_API_BASE_URL`, then deploy to Azure Static Web Apps.

Pull requests run only the tests.

One-time setup, done once in this order:

1. **Database:** create a free Postgres on [Neon](https://neon.tech) (Singapore region; use the direct, non-pooled connection string) or [Supabase](https://supabase.com) (use the *Session pooler* string, because Azure has no IPv6). The backend accepts the `postgresql://…?sslmode=require` URL as-is.
2. **Log in:** run `az login` and `gh auth login`.
3. **Repository:** commit locally, then create the GitHub repository without pushing:
   - `git init -b main && git add . && git commit -m "Initial commit"`
   - `gh repo create varun00391/voice_assisted_system --public --source . --remote origin`
4. **Azure resources:** run `./infra/azure-setup.sh`. It creates the resource group, registry, Container Apps environment and app (`minReplicas=0`), Static Web App, managed identities (AcrPull for image pulls; an OIDC deploy identity limited to `main`) and the GitHub variables/secret.
5. **Secrets:** run `./infra/azure-secrets.sh` yourself. It stores `GROQ_API_KEY`, `EURON_API_KEY`, `DATABASE_URL` and `API_ACCESS_KEY` as Container Apps secrets, and copies the non-secret LLM settings from `.env`.
6. **First deployment:** run `git push -u origin main`. Then open the frontend URL and enter the access key on the Settings page.

To roll back, redeploy an earlier image. Either re-run the backend workflow for that commit in GitHub Actions, or run `az containerapp update -n voice-assistant-api -g voice-assistant-rg --image <acr>.azurecr.io/voice-assistant-backend:<older-sha>`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness and deployed version (no access key needed) |
| POST | `/api/v1/transcribe` | Audio (multipart `audio`) → transcript |
| POST | `/api/v1/chat` | Question + mode (+ optional preferred `provider`) → answer |
| POST | `/api/v1/voice/chat` | Audio + mode (+ optional `provider`) → transcript and answer |
| GET | `/api/v1/modes` | Available answer modes |
| GET/DELETE | `/api/v1/conversations[/{id}]` | Conversation history |
| GET/POST/PATCH/DELETE | `/api/v1/user/context` | User-provided persistent context |
| GET | `/api/v1/providers/health` | LLM provider circuit-breaker state |
