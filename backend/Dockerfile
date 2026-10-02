FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/app \
    HF_HOME=/home/app/.cache/huggingface

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /home/app/.cache/huggingface \
    && chown -R app:app /home/app /app

USER app

# Bake the Whisper model into the image (CI sets this) so cold starts don't download it.
# Must match the runtime WHISPER_MODEL; leave empty locally, where a volume caches the model.
ARG WHISPER_PRELOAD_MODEL=""
RUN if [ -n "$WHISPER_PRELOAD_MODEL" ]; then \
        python -c "import sys; from faster_whisper import download_model; download_model(sys.argv[1])" "$WHISPER_PRELOAD_MODEL"; \
    fi

COPY --chown=app:app app ./app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# Behind nginx / Azure ingress the client IP arrives in X-Forwarded-For; the rate limiter needs it.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
