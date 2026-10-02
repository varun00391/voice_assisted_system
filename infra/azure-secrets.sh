#!/usr/bin/env bash
# Stores the backend's secrets as Azure Container Apps secrets and syncs non-secret LLM settings from .env.
# Run it yourself in a terminal: secret values are typed (hidden) or read from .env, never printed or saved.
# Re-run any time a key changes; it creates a new revision so the new values take effect.
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-voice-assistant-rg}"
CONTAINER_APP="${CONTAINER_APP:-voice-assistant-api}"
ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"

# Non-secret settings copied from .env when set there. WHISPER_MODEL is excluded: it is baked into the image.
SYNCED_SETTINGS=(
  LLM_PROVIDER_ORDER LLM_TIMEOUT_SECONDS LLM_TEMPERATURE LLM_MAX_TOKENS LLM_MAX_CONTINUATIONS
  GROQ_MODEL GROQ_REASONING_FORMAT GROQ_REASONING_EFFORT EURON_MODEL
  WHISPER_LANGUAGE MAX_AUDIO_SIZE_MB MAX_AUDIO_DURATION_SECONDS MAX_HISTORY_MESSAGES RATE_LIMIT_PER_MINUTE
)

env_value() {
  [ -f "$ENV_FILE" ] || return 0
  grep -E "^$1=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//' || true
}

# Reuses the .env value (after confirmation) unless it is missing or still a placeholder.
read_secret() {
  local name=$1 prompt=$2 value answer
  value=$(env_value "$name")
  if [ -n "$value" ] && [[ "$value" != replace-with* ]]; then
    read -rp "Use $name from .env? [Y/n] " answer
    if [[ ! "$answer" =~ ^[Nn] ]]; then
      printf '%s' "$value"
      return
    fi
  fi
  read -rsp "$prompt: " value
  echo >&2
  printf '%s' "$value"
}

az containerapp show -n "$CONTAINER_APP" -g "$RESOURCE_GROUP" -o none

GROQ_API_KEY=$(read_secret GROQ_API_KEY "Groq API key")
EURON_API_KEY=$(read_secret EURON_API_KEY "Euron API key (Enter to skip)")
echo "Paste the Postgres connection string from Neon or Supabase (postgresql://...?sslmode=require)."
read -rsp "DATABASE_URL: " DATABASE_URL
echo
read -rsp "Access key for the web app (Enter to generate one): " API_ACCESS_KEY
echo
GENERATED_KEY=false
if [ -z "$API_ACCESS_KEY" ]; then
  API_ACCESS_KEY=$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | cut -c1-40)
  GENERATED_KEY=true
fi

[ -n "$GROQ_API_KEY" ] || { echo "GROQ_API_KEY is required." >&2; exit 1; }
[[ "$DATABASE_URL" == postgres* ]] || { echo "DATABASE_URL must be a postgres:// or postgresql:// URL." >&2; exit 1; }

secrets=("groq-api-key=$GROQ_API_KEY" "database-url=$DATABASE_URL" "api-access-key=$API_ACCESS_KEY")
env_vars=(GROQ_API_KEY=secretref:groq-api-key DATABASE_URL=secretref:database-url API_ACCESS_KEY=secretref:api-access-key)
if [ -n "$EURON_API_KEY" ]; then
  secrets+=("euron-api-key=$EURON_API_KEY")
  env_vars+=(EURON_API_KEY=secretref:euron-api-key)
fi

for name in "${SYNCED_SETTINGS[@]}"; do
  value=$(env_value "$name")
  [ -n "$value" ] && env_vars+=("$name=$value")
done
# Forces a new revision so updated secret values are picked up even when no env var changed.
env_vars+=("SECRETS_UPDATED_AT=$(date +%s)")

echo "Storing secrets in $CONTAINER_APP..."
az containerapp secret set -n "$CONTAINER_APP" -g "$RESOURCE_GROUP" --secrets "${secrets[@]}" -o none
az containerapp update -n "$CONTAINER_APP" -g "$RESOURCE_GROUP" --set-env-vars "${env_vars[@]}" -o none

echo "Done. Secrets stored; a new revision is rolling out."
if [ "$GENERATED_KEY" = true ]; then
  echo
  echo "Generated access key (enter it once on the app's Settings page, and keep it somewhere safe):"
  echo "  $API_ACCESS_KEY"
fi
