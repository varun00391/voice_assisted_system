# Voice-Assisted Multi-LLM AI Assistant — Implementation Plan

## 1. Project Overview

Build a voice-assisted AI application where:

1. The user speaks a question through a microphone.
2. The system converts speech to text.
3. The user selects how the answer should be generated, such as:
   - Learning
   - Interview
   - Research
   - Concise
   - Technical
   - Other/custom modes
4. The backend combines:
   - Transcribed question
   - Selected answer mode
   - Conversation history
   - User-provided persistent context
5. An LLM router sends the request to an available LLM provider.
6. If the primary LLM provider hits a rate limit or another retryable temporary failure, another configured provider handles the request.
7. The answer is returned as **text only**.
8. The frontend presents the conversation in a ChatGPT/Gemini-like interface.

### Initial technology choices

- Backend: Python + FastAPI
- Frontend: React + Tailwind CSS
- STT: `faster-whisper` / local Whisper implementation as the primary approach
- LLM providers:
  - Groq
  - Euron
- LLM routing: custom provider abstraction + fallback router
- Memory:
  - Conversation memory
  - User-provided persistent context
- Containerization: Docker
- Future deployment target: Azure/AWS or another cloud platform

### Plan update — split services, Docker, and secrets

Keep backend and frontend as **two separate folders**, each with its own Dockerfile. One root `docker-compose.yml` starts both. Secrets live in a committed `.env.example` (placeholders only) and a local empty `.env` that is filled by the developer and never committed.

```text
voice_assisted_system/
│
├── backend/                 # FastAPI + STT + LLM router
│   └── Dockerfile
│
├── frontend/                # React + Tailwind
│   └── Dockerfile
│
├── docker-compose.yml       # starts backend + frontend (+ database)
├── .env.example             # committed secret names + placeholder values
├── .env                     # empty locally; fill with real keys
└── voice_assisted_system_plan.md
```

Local start:

```bash
cp .env.example .env
# fill API keys and passwords in .env
docker compose up --build
```

See **§24 Configuration**, **§29 Docker**, and **§35 Initial Repository Structure** for the full file contents and compose layout.

### Implementation status (V1)

V1 is implemented in `backend/` and `frontend/`. Phases 1–9 are complete; phase 10 (cloud deployment) is not started.

Verified:

- 52 backend tests (router fallback, circuit breaker, provider error classification, prompt and context selection, all APIs) and 10 frontend tests.
- `docker compose up --build`: WAV, WebM/Opus (Chrome) and M4A (Safari) recordings transcribe in the container.
- Groq 429 → Euron fallback, with every attempt written to `llm_request_logs` in Postgres.

Implementation decisions beyond this plan:

- V1 is single-user (`LOCAL_USER_ID`). Add authentication before exposing it publicly (§25).
- Tables are created on startup. Introduce Alembic migrations before the schema changes in production.
- Context relevance (§16) is rule-based: preferences are always included; career fields for interview-type questions or mode; learning fields for learning; skills when one is mentioned; everything when the user asks about "me/my".
- Non-retryable provider errors (bad key, bad request) are surfaced as HTTP 502 and do not fall back (§11.4). Only retryable failures count toward the circuit breaker.
- If the LLM call fails, the question is not persisted, so a failed first question does not leave an empty conversation.
- A text input sits next to the microphone as a fallback for testing, or when no microphone is available.
- Complete, clean answers:
  - `<think>…</think>` reasoning from reasoning models (e.g. Qwen on Groq) is stripped from answers and from stored history.
  - `GROQ_REASONING_FORMAT=hidden` asks Groq to omit the reasoning entirely.
  - When the provider reports `finish_reason=length`, the router asks the same provider to continue, up to `LLM_MAX_CONTINUATIONS` times, and joins the parts.
  - If the token budget ran out before any answer text, that counts as a retryable `incomplete` failure and falls back to the next provider.
  - Answers still cut off after the continuations are returned with `truncated: true`, and the UI shows a notice.
- Answers render GitHub-flavoured Markdown, single line breaks and LaTeX math (KaTeX; `\( \)`, `\[ \]` and `$$`). Wide tables and code blocks scroll horizontally. The chat column is up to 1152px wide, with answers using the full width.
- Custom-mode instructions are kept in browser storage (Settings page) and sent with each request.

---

# 2. Goals

## Primary goals

- Voice-first user input.
- Text-only AI responses.
- Simple and responsive UI.
- Multiple answer modes.
- Multiple LLM providers.
- Automatic LLM fallback when a provider is temporarily unavailable or rate limited.
- Conversation memory.
- User-provided contextual information that can be used in future answers.
- Clean architecture that allows additional providers to be added without changing business logic.

## Secondary goals

- Track provider failures and latency.
- Make model/provider selection configurable.
- Keep STT and LLM layers independent.
- Keep the application extensible for future RAG and agentic workflows.
- Make the application deployable using Docker (`backend/Dockerfile`, `frontend/Dockerfile`, root `docker-compose.yml`).

---

# 3. Non-Goals for V1

The following should NOT be implemented initially unless requirements change:

- Text-to-speech / voice responses.
- Complex autonomous agents.
- Multi-agent workflows.
- RAG over large document collections.
- Web search.
- Real-time streaming audio conversations.
- Complex enterprise authentication/authorization.
- Advanced model benchmarking.
- Fine-tuning models.

These can be added later without changing the core architecture.

---

# 4. High-Level Architecture

```text
                         ┌─────────────────────┐
                         │       React UI      │
                         │     Tailwind CSS    │
                         └──────────┬──────────┘
                                    │
                          Voice recording
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │       Backend       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      STT Layer      │
                         │                     │
                         │   faster-whisper   │
                         └──────────┬──────────┘
                                    │
                              Transcribed text
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Request Processor  │
                         │                     │
                         │ • Answer mode       │
                         │ • User context      │
                         │ • Conversation      │
                         │   history           │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Prompt Builder    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     LLM Router      │
                         └──────────┬──────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
                     ▼                             ▼
              ┌─────────────┐               ┌─────────────┐
              │    Groq     │               │    Euron    │
              └──────┬──────┘               └──────┬──────┘
                     │                             │
                     └──────────────┬──────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Text Response     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      React UI       │
                         │   Display response  │
                         └─────────────────────┘
```

---

# 5. Core Request Lifecycle

```text
User clicks microphone
        ↓
Frontend records audio
        ↓
Audio uploaded to FastAPI
        ↓
STT service
        ↓
Transcribed question
        ↓
Validate request
        ↓
Load selected answer mode
        ↓
Load conversation history
        ↓
Load relevant user context
        ↓
Build LLM messages
        ↓
LLM Router
        ↓
Primary provider
        │
        ├── Success → response
        │
        └── Retryable failure
                    ↓
               Next provider
                    ↓
                 response
        ↓
Persist conversation
        ↓
Return JSON response
        ↓
Frontend displays text
```

---

# 6. Speech-to-Text Design

## 6.1 Primary STT

Use a local Whisper implementation, preferably `faster-whisper`, rather than sending audio to an external STT API for V1.

### Reasons

- No per-request STT API cost.
- No external STT provider rate limit.
- Better privacy because audio can remain under application control.
- Easy to replace later.
- Consistent with the goal of building a provider-independent AI system.

## 6.2 STT abstraction

Do not couple the application directly to Whisper.

Create an interface similar to:

```python
class STTProvider:
    async def transcribe(self, audio_file) -> str:
        ...
```

Possible implementations:

```text
STTProvider
    │
    ├── FasterWhisperProvider
    ├── GroqWhisperProvider       # future/optional
    └── DeepgramProvider          # future/optional
```

## 6.3 Model selection

Start with a practical Whisper model appropriate for the deployment hardware.

Make the model configurable through environment variables/configuration rather than hardcoding it.

Example:

```env
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

If the deployment machine has a suitable GPU, configuration can be changed without changing application code.

## 6.4 Future Deepgram consideration

Deepgram can be added later if hosted/low-latency STT becomes more important than local inference.

The STT abstraction should therefore prevent Whisper-specific assumptions from leaking into the rest of the system.

---

# 7. Answer Modes

Answer modes are a first-class part of the application.

Initial modes:

```text
Learning
Interview
Research
Concise
Technical
Detailed
Custom
```

## 7.1 Learning mode

Characteristics:

- Explain from fundamentals.
- Progressive explanation.
- Use simple examples.
- Explain technical terminology.
- End with key takeaways when appropriate.

Example system instruction:

```text
Explain the topic in a progressive learning-oriented manner.
Start with intuition, then explain the technical details.
Use examples where useful.
Avoid unnecessary jargon.
```

## 7.2 Interview mode

Characteristics:

- Interview-ready answer.
- Structured response.
- Technical depth.
- Important points an interviewer may expect.
- Possible follow-up questions.
- Avoid unnecessarily long explanations unless requested.

Example:

```text
Answer as an interview preparation assistant.
Give a concise but technically strong answer.
Highlight concepts an interviewer would expect.
Where useful, include examples and likely follow-up questions.
```

## 7.3 Research mode

Characteristics:

- Detailed explanation.
- Separate facts from assumptions.
- Structured sections.
- Explain trade-offs.
- Suitable for later integration with web search/RAG.

Important: research mode does not automatically imply web browsing in V1.

## 7.4 Concise mode

Characteristics:

- Short answer.
- Directly address the question.
- Avoid unnecessary examples unless required.

## 7.5 Technical mode

Characteristics:

- Assume technical background.
- Use correct terminology.
- Focus on implementation details, architecture and trade-offs.

## 7.6 Custom mode

Allow the user to eventually provide custom instructions such as:

```text
Explain everything like a senior AI architect.
Use Python examples.
Keep answers below 500 words.
```

---

# 8. Mode Configuration

Avoid hardcoding mode behavior throughout the codebase.

Use a centralized configuration:

```python
ANSWER_MODES = {
    "learning": {...},
    "interview": {...},
    "research": {...},
    "concise": {...},
    "technical": {...}
}
```

Each mode can contain:

```text
name
description
system_instruction
verbosity
technical_depth
include_examples
include_followups
```

Future configuration can be moved to a database if required.

---

# 9. LLM Provider Architecture

The application must not directly call Groq/Euron from business logic.

Create a common interface.

Example:

```python
class LLMProvider:
    async def generate(
        self,
        messages,
        model,
        temperature=0.2,
        max_tokens=None
    ):
        ...
```

Implement:

```text
LLMProvider
    │
    ├── GroqProvider
    └── EuronProvider
```

Future:

```text
    ├── OpenAIProvider
    ├── AnthropicProvider
    ├── GeminiProvider
    └── AzureOpenAIProvider
```

---

# 10. LLM Router

The LLM Router is responsible for:

- Provider priority.
- Provider availability.
- Retryable errors.
- Rate-limit fallback.
- Timeouts.
- Provider selection.
- Logging provider attempts.
- Returning the successful response.

Example configuration:

```yaml
providers:
  - name: groq
    priority: 1
    enabled: true

  - name: euron
    priority: 2
    enabled: true
```

## 10.1 User-selected provider

The chat UI has an **LLM** selector next to the answer mode:

```text
Auto (Groq → Euron)   # configured LLM_PROVIDER_ORDER
Groq                  # try Groq first, fall back to Euron
Euron                 # try Euron first, fall back to Groq
```

- `POST /api/v1/chat` and `POST /api/v1/voice/chat` accept an optional `provider` (`null`/`"auto"` = configured order).
- The router moves the selected provider to the front and keeps the others, in configured order, as fallbacks. Fallback works in both directions.
- Fallback rules are unchanged (§11): retryable failures (429, 5xx, timeout, connection error) or an open circuit fall back; non-retryable errors (bad key, bad request) do not.
- An unknown or unconfigured provider returns `400 provider_not_configured`.
- Each answer shows "Answered by X", noting when fallback was used. The selection is remembered in browser storage.

---

# 11. Fallback Strategy

## 11.1 Primary scenario

```text
Request
  ↓
Groq
  ↓
Success
  ↓
Return response
```

## 11.2 Rate-limit scenario

```text
Request
  ↓
Groq
  ↓
429 / rate limit
  ↓
Euron
  ↓
Success
  ↓
Return response
```

## 11.3 Temporary server failure

Retryable failures may include:

- HTTP 429
- Temporary 5xx errors
- Timeout
- Connection failure
- Temporary provider unavailability

These should trigger fallback according to configured policy.

## 11.4 Non-retryable failures

Do not blindly fallback for:

- Invalid API key
- Invalid request schema
- Invalid model configuration
- Unsupported parameters
- Application programming errors

These should be logged and surfaced appropriately.

---

# 12. Circuit Breaker / Provider Health

Implement a simple provider-health mechanism after the basic fallback works.

Example:

```text
Groq
 ├── healthy
 ├── degraded
 └── unavailable
```

If Groq repeatedly returns rate limits/server errors:

```text
Groq
   ↓
Failure threshold reached
   ↓
Temporarily disable provider
   ↓
Use Euron directly
   ↓
After cooldown
   ↓
Perform health check
   ↓
Re-enable Groq
```

This prevents repeatedly wasting latency on a provider that is temporarily unavailable.

---

# 13. Provider Observability

For every LLM request, internally record:

```json
{
  "request_id": "uuid",
  "provider_attempts": [
    {
      "provider": "groq",
      "status": "rate_limited",
      "latency_ms": 800
    },
    {
      "provider": "euron",
      "status": "success",
      "latency_ms": 1500
    }
  ],
  "final_provider": "euron"
}
```

Do not necessarily expose all provider details to the normal user interface.

This information will be extremely useful for debugging free-tier limits.

---

# 14. Conversation Memory

The system needs two different types of memory.

## 14.1 Short-term conversation memory

Stores:

```text
Current conversation
Previous user questions
Previous assistant answers
Current mode
Session metadata
```

Example:

```text
User:
What is RAG?

Assistant:
RAG is...

User:
Why do we need embeddings?

Assistant:
Embeddings convert...
```

The second question should be interpreted using relevant conversation context.

## 14.2 Persistent user context

User can explicitly provide information such as:

```text
Name
Professional background
Experience
Skills
Preferences
Learning goals
Interview goals
Other information
```

Example:

```json
{
  "professional_background": "Data Scientist",
  "experience_years": 10,
  "skills": [
    "Python",
    "Machine Learning",
    "LLM",
    "RAG",
    "FastAPI"
  ],
  "goal": "Prepare for Senior AI Architect interviews"
}
```

The application can use this information when generating responses.

---

# 15. User Context Management

Create APIs to allow the user to:

```text
GET    /api/v1/user/context
POST   /api/v1/user/context     # replace
PATCH  /api/v1/user/context     # merge
DELETE /api/v1/user/context
```

The user should explicitly control what information is stored.

Avoid automatically treating every conversation statement as persistent memory in V1.

---

# 16. Memory Injection Strategy

Do not blindly inject all user information into every prompt.

Use relevant context only.

Conceptually:

```text
Question
   +
Relevant conversation history
   +
Relevant user context
   +
Answer mode
   ↓
Prompt Builder
```

Example:

If user asks:

> "How should I prepare for this interview?"

Professional background and interview goals are relevant.

If user asks:

> "What is a vector database?"

Only relevant context should be included, if needed.

---

# 17. Database

For V1, use a database that can store:

### User

```text
user_id
profile/context
created_at
updated_at
```

### Conversation

```text
conversation_id
user_id
title
mode
created_at
updated_at
```

### Message

```text
message_id
conversation_id
role
content
created_at
```

### LLM request log

```text
request_id
conversation_id
provider
model
status
latency
error_type
created_at
```

A relational database such as PostgreSQL is a good default.

MongoDB can also work, particularly if the user-context schema is expected to evolve rapidly.

For the first implementation, keep the persistence layer abstract enough that the database can be changed later.

---

# 18. API Design

## 18.1 Health

```http
GET /health
```

Response:

```json
{
  "status": "healthy"
}
```

## 18.2 Transcription

```http
POST /api/v1/transcribe
```

Input:

```text
multipart/form-data
audio=<file>
```

Response:

```json
{
  "text": "Explain RAG architecture"
}
```

## 18.3 Chat

```http
POST /api/v1/chat
```

Request:

```json
{
  "conversation_id": "uuid",
  "message": "Explain RAG architecture",
  "mode": "interview"
}
```

Response:

```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "answer": "RAG stands for...",
  "provider": "groq",
  "fallback_used": false
}
```

Provider details can later be hidden from the frontend if desired.

## 18.4 Voice-to-answer

For better UX, eventually expose:

```http
POST /api/v1/voice/chat
```

Flow:

```text
Audio
 ↓
STT
 ↓
Chat pipeline
 ↓
LLM
 ↓
Text response
```

Response:

```json
{
  "transcript": "Explain RAG architecture",
  "answer": "RAG stands for...",
  "mode": "interview",
  "provider": "euron"
}
```

---

# 19. Frontend Architecture

Use:

```text
React
Tailwind CSS
```

The frontend is a **separate top-level folder** (`frontend/`) with its own Dockerfile. It talks to the backend over HTTP (`VITE_API_BASE_URL`). Do not colocate React code inside the FastAPI tree.

Suggested structure:

```text
frontend/
│
├── src/
│   ├── components/
│   │   ├── ChatWindow/
│   │   ├── Message/
│   │   ├── VoiceButton/
│   │   ├── ModeSelector/
│   │   ├── ConversationList/
│   │   └── UserContext/
│   │
│   ├── pages/
│   │   ├── Chat/
│   │   ├── Settings/
│   │   └── Profile/
│   │
│   ├── services/
│   │   └── api.js
│   │
│   ├── hooks/
│   │   └── useVoiceRecorder.js
│   │
│   └── App.jsx
```

---

# 20. Main UI

The UI should resemble modern AI chat applications.

Core elements:

```text
┌─────────────────────────────────────────────┐
│ AI Voice Assistant                         │
├─────────────────────────────────────────────┤
│                                             │
│ Mode: [ Interview ▼ ]                       │
│                                             │
│ User                                       │
│ ┌─────────────────────────────────────────┐ │
│ │ Explain RAG architecture                │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ AI                                          │
│ ┌─────────────────────────────────────────┐ │
│ │ RAG is a technique...                   │ │
│ │                                         │ │
│ │ 1. Document ingestion                   │ │
│ │ 2. Chunking                             │ │
│ │ 3. Embeddings                           │ │
│ │ 4. Retrieval                            │ │
│ │ 5. Generation                           │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│                  🎤                         │
│              Speak                         │
│                                             │
└─────────────────────────────────────────────┘
```

---

# 21. Voice Interaction

V1 interaction:

```text
Click microphone
       ↓
Start recording
       ↓
User speaks
       ↓
Click/auto stop
       ↓
Upload audio
       ↓
Transcription
       ↓
Show transcript
       ↓
LLM request
       ↓
Show answer
```

The transcript should ideally appear as the user's message before the final answer arrives.

Example:

```text
You:
"Explain vector databases."

AI:
[Generating...]

AI:
"A vector database is..."
```

---

# 22. No TTS in V1

Explicit requirement:

```text
Input  → Voice
Output → Text
```

Do not implement:

```text
Text → Voice
```

The architecture can leave room for TTS later but it should not be part of the initial implementation.

---

# 23. Error Handling

Frontend should display useful user-facing messages.

Examples:

### STT failure

```text
Unable to transcribe the audio. Please try again.
```

### All LLM providers unavailable

```text
The AI providers are temporarily unavailable.
Please try again shortly.
```

### Microphone permission

```text
Microphone access is required to use voice input.
```

### Empty transcript

```text
No speech was detected. Please try again.
```

Never expose raw API keys, provider stack traces or sensitive infrastructure details.

---

# 24. Configuration

Use environment variables loaded from a **single root `.env`** (shared by backend, frontend build args, and docker-compose). Do not scatter secrets across `backend/.env` and `frontend/.env`.

Create two files at the project root:

| File | Committed? | Purpose |
| --- | --- | --- |
| `.env.example` | Yes | Documents every secret and config key with placeholders |
| `.env` | No | Empty template the developer fills with real values |

`.env` must be listed in `.gitignore`. Docker Compose reads `.env` automatically and also via `env_file`.

## 24.1 `.env.example`

Committed file at the project root with every key, comments and placeholder values (see the file for the full list). Groups:

| Group | Keys |
| --- | --- |
| Application | `APP_ENV`, `LOG_LEVEL`, `BACKEND_PORT`, `FRONTEND_PORT`, `CORS_ORIGINS` |
| Frontend | `VITE_API_BASE_URL` (blank = same-origin via the nginx `/api` proxy) |
| LLM routing | `LLM_PROVIDER_ORDER`, `LLM_TIMEOUT_SECONDS`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS` (default 4096), `LLM_MAX_CONTINUATIONS`, `CIRCUIT_BREAKER_FAILURE_THRESHOLD`, `CIRCUIT_BREAKER_COOLDOWN_SECONDS` |
| Groq (primary) | `GROQ_API_KEY`, `GROQ_BASE_URL`, `GROQ_MODEL` (default `llama-3.3-70b-versatile`), `GROQ_REASONING_FORMAT`, `GROQ_REASONING_EFFORT` (reasoning models only) |
| Euron (fallback) | `EURON_API_KEY`, `EURON_BASE_URL`, `EURON_MODEL` (default `gpt-4.1-nano`) |
| STT | `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`, `WHISPER_LANGUAGE`, `WHISPER_PRELOAD`, `STT_TIMEOUT_SECONDS`, `MAX_CONCURRENT_TRANSCRIPTIONS` |
| Audio limits | `MAX_AUDIO_SIZE_MB`, `MAX_AUDIO_DURATION_SECONDS` |
| PostgreSQL | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` |
| Local dev DB | `DATABASE_URL` (only used outside Docker; blank = local SQLite) |
| Memory / protection | `MAX_HISTORY_MESSAGES`, `RATE_LIMIT_PER_MINUTE` |

Redis is not used in V1, so no `REDIS_URL` key is defined.

## 24.2 Empty `.env`

The root `.env` contains the same keys with blank values. Blank values fall back to backend defaults (`env_ignore_empty`), except `POSTGRES_PASSWORD`, which docker compose requires. A provider whose key is blank or still a `replace-with-…` placeholder is disabled.

Developer workflow:

```bash
cp .env.example .env
# then replace every placeholder with a real value
```

Use a settings class rather than directly accessing environment variables throughout the application.

---

# 25. Security

At minimum:

- Never commit API keys.
- Commit `.env.example` only (placeholders). Keep `.env` local and gitignored.
- Use `.env` locally; docker-compose loads it into the backend and uses it for Postgres variables. The frontend container receives no secrets, only the `VITE_API_BASE_URL` build arg.
- Use cloud secret management in production.
- Validate uploaded audio files.
- Limit maximum audio size.
- Limit audio duration.
- Validate MIME type.
- Sanitize user-provided custom prompts/context.
- Never expose provider credentials to React.
- Add authentication before exposing persistent user data publicly.
- Apply API rate limiting to protect the application itself.

---

# 26. Audio Security and Resource Controls

Because Whisper inference can be computationally expensive:

Implement:

```text
Maximum file size
Maximum recording duration
Allowed audio formats
Request timeout
Concurrent transcription limit
```

For example:

```text
Audio upload
    ↓
Validate size
    ↓
Validate format
    ↓
Validate duration
    ↓
Transcribe
```

Exact limits should be configurable.

---

# 27. Logging

Use structured logging.

Every request should have a `request_id`.

Example:

```text
request_id=abc123
STT started

request_id=abc123
STT completed
duration=1.8s

request_id=abc123
LLM provider=groq
status=429

request_id=abc123
Fallback provider=euron

request_id=abc123
LLM completed
duration=2.1s
```

Avoid logging:

- API keys
- Sensitive user information
- Full private conversations unless explicitly required for debugging

---

# 28. Testing Strategy

## Unit tests

Test:

- Mode selection.
- Prompt generation.
- STT provider interface.
- LLM provider interface.
- Router.
- Retry logic.
- Rate-limit fallback.
- Provider health state.
- Context selection.
- Conversation persistence.

## Integration tests

Test:

```text
Audio
 ↓
STT
 ↓
Chat
 ↓
LLM
 ↓
Response
```

## Failure tests

Simulate:

```text
Groq 429
Groq timeout
Groq 500
Euron success
Euron failure
All providers fail
```

Verify that fallback behaves correctly.

## Frontend tests

Test:

- Microphone permissions.
- Recording state.
- Mode switching.
- Transcript rendering.
- Loading state.
- Error state.
- Conversation rendering.

---

# 29. Docker

V1 packaging uses **two Dockerfiles** and **one compose file**:

```text
backend/Dockerfile
frontend/Dockerfile
docker-compose.yml          # project root; starts both apps
```

Secrets and ports come from the root `.env`. Do not bake API keys into images.

## 29.1 Backend Dockerfile

`backend/Dockerfile` — FastAPI + faster-whisper on `python:3.12-slim-bookworm`.

- Runs as a non-root `app` user; `HF_HOME=/home/app/.cache/huggingface` holds the Whisper model cache.
- No system `ffmpeg`: faster-whisper decodes audio through PyAV, whose wheels bundle FFmpeg. Only `curl` is installed, for the healthcheck.
- `requirements.txt` pins `av<19`: PyAV 19 removed an `av.open()` argument that faster-whisper 1.2.x uses.
- A single uvicorn worker, because the circuit breaker, rate limiter and Whisper model are in-process state.

## 29.2 Frontend Dockerfile

`frontend/Dockerfile` — multi-stage build: `node:22-alpine` runs `npm ci && npm run build`, then `nginx:1.27-alpine` serves `dist/`.

`frontend/nginx.conf`:

- proxies `/api/` and `/health` to `http://backend:8000`, so the browser calls a same-origin API and `VITE_API_BASE_URL` can stay blank;
- sets `client_max_body_size 25m` (nginx defaults to 1 MB, which would reject recordings) and a 180 s proxy timeout for slow CPU transcription;
- falls back to `index.html` for SPA routes.

## 29.3 Common docker-compose.yml

Root `docker-compose.yml` starts `postgres`, `backend` and `frontend`. Redis is omitted from V1.

- `postgres`: `postgres:16-alpine`; port bound to `127.0.0.1` only; `POSTGRES_PASSWORD` is required (`${POSTGRES_PASSWORD:?…}`).
- `backend`: `env_file: .env`, plus `DATABASE_URL` built from the `POSTGRES_*` values so the password lives in one place; waits for a healthy Postgres; the `whisper_models` volume persists downloaded models.
- `frontend`: build arg `VITE_API_BASE_URL` only. It does **not** load `.env`, so no API keys reach that container.
- Named volumes: `postgres_data`, `whisper_models`.

Start everything:

```bash
cp .env.example .env   # first time only; then fill secrets
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/health`

Redis is optional for V1 but useful later for:

- Rate limiting
- Caching
- Provider health
- Background jobs
- Session state

Do not add Redis to compose until a later phase actually needs it.

---

# 30. Suggested Development Phases

## Phase 1 — Project foundation

- Create `backend/` and `frontend/` as separate top-level folders.
- Add `backend/Dockerfile` and `frontend/Dockerfile`.
- Add a single root `docker-compose.yml` that starts backend and frontend (and Postgres).
- Add root `.env.example` with every secret/config key and placeholder values.
- Add root empty `.env` (gitignored) for local keys.
- Add `.gitignore` that excludes `.env` and includes `.env.example`.
- Create FastAPI backend skeleton and health endpoint.
- Create React + Tailwind frontend skeleton.
- Confirm `docker compose up --build` starts both services.

## Phase 2 — Local STT

- Integrate faster-whisper.
- Create STT provider abstraction.
- Implement audio upload endpoint.
- Validate audio.
- Return transcript.
- Build microphone UI.
- Display transcript.

## Phase 3 — Single LLM

- Integrate Groq.
- Create LLM provider abstraction.
- Build prompt builder.
- Create `/chat`.
- Display text answer.

## Phase 4 — Answer modes

Implement:

- Learning
- Interview
- Research
- Concise
- Technical

Add mode selector to frontend.

## Phase 5 — Multi-provider LLM

- Add Euron.
- Implement LLM router.
- Implement provider priority.
- Implement rate-limit detection.
- Implement timeout handling.
- Implement fallback.
- Add provider attempt logging.

## Phase 6 — Conversation memory

- Add conversation model.
- Add message model.
- Persist conversations.
- Load relevant history.
- Display conversation list.
- Add new conversation functionality.

## Phase 7 — User context

- Add user context storage.
- Add context management UI.
- Allow user to explicitly add/update/delete information.
- Integrate relevant context into prompt construction.

## Phase 8 — Reliability

- Provider health.
- Circuit breaker.
- Request IDs.
- Structured logging.
- Better error handling.
- Rate limiting.
- Audio resource limits.

## Phase 9 — Testing

- Unit tests.
- Integration tests.
- Provider fallback tests.
- STT tests.
- Frontend tests.
- End-to-end voice workflow tests.

## Phase 10 — Deployment

- Reuse the same `backend/Dockerfile`, `frontend/Dockerfile`, and `docker-compose.yml` (production overlay if needed).
- Cloud deployment.
- Secret management from `.env` / cloud secrets — never bake keys into images.
- HTTPS.
- Monitoring.
- Application-level rate limiting.

---

# 31. Future Extensions

The architecture should support the following without major redesign.

## Additional LLM providers

```text
OpenAI
Anthropic
Gemini
Azure OpenAI
Local LLM
```

## Additional STT providers

```text
Deepgram
Groq Whisper
Azure Speech
Google Speech
```

## RAG

```text
Question
   ↓
Retriever
   ↓
Relevant documents
   ↓
LLM Router
   ↓
Answer
```

Possible future vector databases:

- Qdrant
- FAISS
- pgvector

## Agentic workflows

Later, LangGraph can be introduced for workflows such as:

```text
Question
   ↓
Intent classification
   ↓
Need RAG?
   ├── No → LLM
   │
   └── Yes
         ↓
      Retrieval
         ↓
      Reranking
         ↓
        LLM
         ↓
      Validation
```

## Interview simulator

A future Interview Mode can become interactive:

```text
AI asks question
       ↓
User answers by voice
       ↓
STT
       ↓
Answer evaluator
       ↓
Score/feedback
       ↓
Follow-up question
       ↓
User responds
```

The evaluation system should remain separate from the core voice/LLM routing layer.

---

# 32. Important Architectural Principles

### Principle 1 — Provider independence

Business logic should never directly depend on Groq or Euron.

Use:

```python
llm_router.generate(...)
```

instead of:

```python
groq_client.chat.completions.create(...)
```

throughout the application.

### Principle 2 — STT independence

The application should depend on:

```python
stt_provider.transcribe(...)
```

not directly on Whisper implementation details.

### Principle 3 — Mode independence

Answer modes should be configuration/prompt policies, not separate hardcoded application flows.

### Principle 4 — Memory separation

Keep:

```text
Conversation memory
```

separate from:

```text
Persistent user context
```

### Principle 5 — Fallback transparency internally

Record which provider was attempted and why fallback occurred, even if the normal UI does not expose it.

### Principle 6 — Fail gracefully

A temporary external-provider failure should not crash the application.

### Principle 7 — Keep V1 simple

Do not introduce LangGraph, RAG, agents, Redis and multiple databases until they solve an actual requirement.

---

# 33. Proposed Final Architecture

```text
                         USER
                           │
                           │ Voice
                           ▼
                  ┌──────────────────┐
                  │    React UI      │
                  │ Tailwind CSS     │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │     FastAPI      │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │   STT Gateway    │
                  │                  │
                  │ faster-whisper   │
                  └────────┬─────────┘
                           │
                     Transcribed text
                           │
                           ▼
              ┌──────────────────────────┐
              │    Request Processor     │
              │                          │
              │ • Mode                   │
              │ • Conversation           │
              │ • User context           │
              └────────────┬─────────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │  Prompt Builder  │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │    LLM Router    │
                  │                  │
                  │ Priority/Fallback│
                  └───────┬──────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
        ┌───────────┐           ┌───────────┐
        │   Groq    │           │   Euron   │
        └─────┬─────┘           └─────┬─────┘
              │                       │
              └───────────┬───────────┘
                          │
                          ▼
                  ┌──────────────────┐
                  │  Text Response   │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │    React UI      │
                  │ ChatGPT-style    │
                  └──────────────────┘

             ┌─────────────────────────────┐
             │       Persistence           │
             │                             │
             │ Conversations              │
             │ Messages                   │
             │ User Context               │
             │ Provider Logs              │
             └─────────────────────────────┘
```

---

# 34. V1 Definition of Done

V1 is complete when a user can:

1. Open the React application.
2. Select an answer mode.
3. Click the microphone.
4. Speak a question.
5. Stop recording.
6. See the transcribed question.
7. Have the question sent to the backend.
8. Have the selected mode influence the response.
9. Receive a text answer.
10. Continue the conversation using voice.
11. Have previous messages available within the conversation.
12. Add user-specific context.
13. Have relevant user context used in answers.
14. Use Groq as the primary LLM.
15. Automatically fall back to Euron when the configured primary provider encounters a retryable rate-limit/temporary failure.
16. See a useful error if all configured providers fail.
17. Run the complete system locally with `docker compose up --build` after filling `.env` from `.env.example`.

---

# 35. Initial Repository Structure

Backend and frontend are **separate folders**, each with its own Dockerfile. Compose, env files, and this plan live at the project root.

```text
voice_assisted_system/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py              # dependency wiring (session, router, STT, user)
│   │   │   ├── health.py            # /health, /api/v1/config, /api/v1/providers/health
│   │   │   ├── modes.py
│   │   │   ├── voice.py             # /transcribe, /voice/chat
│   │   │   ├── chat.py
│   │   │   ├── conversations.py
│   │   │   └── user_context.py
│   │   │
│   │   ├── core/                    # errors, JSON logging, request-id + rate-limit middleware
│   │   │
│   │   ├── services/
│   │   │   ├── stt/                 # upload validation, concurrency + timeout
│   │   │   ├── llm/                 # router + circuit breaker
│   │   │   ├── modes/               # ANSWER_MODES config
│   │   │   ├── memory/              # conversation store
│   │   │   ├── context/             # user context store + relevance selector
│   │   │   ├── prompt_builder.py
│   │   │   └── chat_service.py      # request processor
│   │   │
│   │   ├── providers/
│   │   │   ├── stt/                 # STTProvider, FasterWhisperProvider
│   │   │   └── llm/                 # LLMProvider, Groq, Euron (OpenAI-compatible)
│   │   │
│   │   ├── models/                  # SQLAlchemy entities + engine
│   │   ├── schemas/
│   │   ├── config/                  # pydantic Settings
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/              # ChatWindow, Message, VoiceButton, ModeSelector,
│   │   │                            # ConversationList, UserContext
│   │   ├── pages/                   # Chat, Profile, Settings
│   │   ├── hooks/                   # useVoiceRecorder
│   │   ├── services/                # api.js, preferences.js
│   │   └── App.jsx
│   │
│   ├── index.html
│   ├── vite.config.js
│   ├── nginx.conf
│   ├── package.json
│   ├── package-lock.json
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
├── .env
├── .gitignore
├── README.md
└── voice_assisted_system_plan.md
```

Rules:

- `backend/Dockerfile` builds only the FastAPI/Whisper image.
- `frontend/Dockerfile` builds only the React/nginx image.
- `docker-compose.yml` is the **only** way to start both containers together.
- `.env.example` is committed and lists every secret with placeholders.
- `.env` is empty until filled locally and is never committed.

---

# 36. Recommended Implementation Order

The implementation should proceed in this exact dependency order:

```text
1. Repository + split folders (backend/, frontend/)
             ↓
2. .env.example + empty .env + Dockerfiles + docker-compose.yml
             ↓
3. FastAPI backend
             ↓
4. React + Tailwind frontend
             ↓
5. Microphone recording
             ↓
6. faster-whisper STT
             ↓
7. Groq integration
             ↓
8. Basic chat UI
             ↓
9. Answer modes
             ↓
10. Euron integration
             ↓
11. LLM fallback router
             ↓
12. Conversation persistence
             ↓
13. User context
             ↓
14. Error handling + observability
             ↓
15. Testing
             ↓
16. Production Docker / secret management
             ↓
17. Deployment
```

This order keeps each stage independently testable and avoids introducing unnecessary complexity before the core voice-to-text-to-answer workflow works.
