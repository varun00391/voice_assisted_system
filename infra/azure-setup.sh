#!/usr/bin/env bash
# One-time Azure + GitHub setup for CI/CD. Safe to re-run: existing resources are reused.
#
# Prerequisites: `az login`, `gh auth login`, and the GitHub repository already exists.
# Usage:         GITHUB_REPO=owner/name ./infra/azure-setup.sh
# Secrets (API keys, database URL, access key) are set separately with ./infra/azure-secrets.sh.
set -euo pipefail

GITHUB_REPO="${GITHUB_REPO:-varun00391/voice_assisted_system}"
LOCATION="${LOCATION:-centralindia}"
# Static Web Apps serves content globally; this region only holds its metadata and must be one SWA supports.
SWA_LOCATION="${SWA_LOCATION:-eastasia}"
RESOURCE_GROUP="${RESOURCE_GROUP:-voice-assistant-rg}"
ENVIRONMENT="${ENVIRONMENT:-voice-assistant-env}"
CONTAINER_APP="${CONTAINER_APP:-voice-assistant-api}"
STATIC_WEB_APP="${STATIC_WEB_APP:-voice-assistant-web}"
LOG_WORKSPACE="${LOG_WORKSPACE:-voice-assistant-logs}"
PULL_IDENTITY="${PULL_IDENTITY:-voice-assistant-acr-pull}"
DEPLOY_IDENTITY="${DEPLOY_IDENTITY:-voice-assistant-github-deploy}"
WHISPER_MODEL="${WHISPER_MODEL:-small}"

# Keep only a GUID. Azure CLI sometimes prints "No module..." on stdout, and the
# first characters of that message are not a valid registry-name suffix.
read_guid() {
  az account show --query "$1" -o tsv \
    | grep -Eo '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}' \
    | head -1 \
    | tr '[:upper:]' '[:lower:]'
}
SUBSCRIPTION_ID=$(read_guid id)
TENANT_ID=$(read_guid tenantId)
if [ -z "$SUBSCRIPTION_ID" ] || [ -z "$TENANT_ID" ]; then
  echo "Could not read the Azure subscription or tenant id. Check: az account show --query '{id:id,tenant:tenantId}' -o json" >&2
  exit 1
fi
# Registry names are global, lowercase, and alphanumeric. The subscription prefix keeps the default unique.
ACR_NAME=$(printf '%s' "${ACR_NAME:-voiceassistant${SUBSCRIPTION_ID:0:8}}" | tr '[:upper:]' '[:lower:]')

step() { printf '\n==> %s\n' "$*"; }

assign_role() {
  local principal_id=$1 role=$2 scope=$3 attempt
  local existing
  existing=$(az role assignment list --assignee "$principal_id" --role "$role" --scope "$scope" --query 'length(@)' -o tsv)
  [ "$existing" != "0" ] && return 0
  # A just-created identity can take a minute to replicate before it can receive roles.
  for attempt in 1 2 3 4 5 6; do
    if az role assignment create --assignee-object-id "$principal_id" --assignee-principal-type ServicePrincipal \
      --role "$role" --scope "$scope" -o none 2>/dev/null; then
      return 0
    fi
    echo "    waiting for identity to replicate (attempt $attempt)..."
    sleep 15
  done
  echo "Could not assign $role on $scope" >&2
  return 1
}

step "Checking GitHub repository $GITHUB_REPO"
gh repo view "$GITHUB_REPO" --json name >/dev/null

step "Registering Azure resource providers (first run can take a few minutes)"
for namespace in Microsoft.App Microsoft.ContainerRegistry Microsoft.OperationalInsights Microsoft.ManagedIdentity Microsoft.Web; do
  az provider register --namespace "$namespace" --wait -o none
done

step "Resource group $RESOURCE_GROUP ($LOCATION)"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" -o none

step "Log Analytics workspace $LOG_WORKSPACE"
az monitor log-analytics workspace show -g "$RESOURCE_GROUP" -n "$LOG_WORKSPACE" -o none 2>/dev/null \
  || az monitor log-analytics workspace create -g "$RESOURCE_GROUP" -n "$LOG_WORKSPACE" -l "$LOCATION" -o none
LOG_CUSTOMER_ID=$(az monitor log-analytics workspace show -g "$RESOURCE_GROUP" -n "$LOG_WORKSPACE" --query customerId -o tsv)
LOG_KEY=$(az monitor log-analytics workspace get-shared-keys -g "$RESOURCE_GROUP" -n "$LOG_WORKSPACE" --query primarySharedKey -o tsv)

step "Container registry $ACR_NAME"
az acr show -n "$ACR_NAME" -g "$RESOURCE_GROUP" -o none 2>/dev/null \
  || az acr create -n "$ACR_NAME" -g "$RESOURCE_GROUP" -l "$LOCATION" --sku Basic --admin-enabled false -o none
ACR_ID=$(az acr show -n "$ACR_NAME" -g "$RESOURCE_GROUP" --query id -o tsv)

step "Container Apps environment $ENVIRONMENT"
az containerapp env show -n "$ENVIRONMENT" -g "$RESOURCE_GROUP" -o none 2>/dev/null \
  || az containerapp env create -n "$ENVIRONMENT" -g "$RESOURCE_GROUP" -l "$LOCATION" \
       --logs-workspace-id "$LOG_CUSTOMER_ID" --logs-workspace-key "$LOG_KEY" -o none

step "Managed identity $PULL_IDENTITY with AcrPull"
az identity show -n "$PULL_IDENTITY" -g "$RESOURCE_GROUP" -o none 2>/dev/null \
  || az identity create -n "$PULL_IDENTITY" -g "$RESOURCE_GROUP" -l "$LOCATION" -o none
PULL_IDENTITY_ID=$(az identity show -n "$PULL_IDENTITY" -g "$RESOURCE_GROUP" --query id -o tsv)
PULL_PRINCIPAL_ID=$(az identity show -n "$PULL_IDENTITY" -g "$RESOURCE_GROUP" --query principalId -o tsv)
assign_role "$PULL_PRINCIPAL_ID" AcrPull "$ACR_ID"

step "Static Web App $STATIC_WEB_APP"
az staticwebapp show -n "$STATIC_WEB_APP" -g "$RESOURCE_GROUP" -o none 2>/dev/null \
  || az staticwebapp create -n "$STATIC_WEB_APP" -g "$RESOURCE_GROUP" -l "$SWA_LOCATION" --sku Free -o none
FRONTEND_HOST=$(az staticwebapp show -n "$STATIC_WEB_APP" -g "$RESOURCE_GROUP" --query defaultHostname -o tsv)

step "Backend Container App $CONTAINER_APP"
if ! az containerapp show -n "$CONTAINER_APP" -g "$RESOURCE_GROUP" -o none 2>/dev/null; then
  # Placeholder image until the first GitHub Actions run pushes the real one; with 0 replicas it never starts.
  az containerapp create -n "$CONTAINER_APP" -g "$RESOURCE_GROUP" --environment "$ENVIRONMENT" \
    --image mcr.microsoft.com/k8se/quickstart:latest \
    --target-port 8000 --ingress external \
    --min-replicas 0 --max-replicas 1 --cpu 2 --memory 4Gi \
    --user-assigned "$PULL_IDENTITY_ID" \
    --registry-server "$ACR_NAME.azurecr.io" --registry-identity "$PULL_IDENTITY_ID" \
    --env-vars APP_ENV=production LOG_LEVEL=INFO "CORS_ORIGINS=https://$FRONTEND_HOST" \
      "WHISPER_MODEL=$WHISPER_MODEL" WHISPER_DEVICE=cpu WHISPER_COMPUTE_TYPE=int8 WHISPER_PRELOAD=true \
      MAX_CONCURRENT_TRANSCRIPTIONS=2 \
    -o none
fi
BACKEND_HOST=$(az containerapp show -n "$CONTAINER_APP" -g "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)
CONTAINER_APP_ID=$(az containerapp show -n "$CONTAINER_APP" -g "$RESOURCE_GROUP" --query id -o tsv)

step "GitHub deploy identity $DEPLOY_IDENTITY (OIDC, main branch only)"
az identity show -n "$DEPLOY_IDENTITY" -g "$RESOURCE_GROUP" -o none 2>/dev/null \
  || az identity create -n "$DEPLOY_IDENTITY" -g "$RESOURCE_GROUP" -l "$LOCATION" -o none
DEPLOY_CLIENT_ID=$(az identity show -n "$DEPLOY_IDENTITY" -g "$RESOURCE_GROUP" --query clientId -o tsv)
DEPLOY_PRINCIPAL_ID=$(az identity show -n "$DEPLOY_IDENTITY" -g "$RESOURCE_GROUP" --query principalId -o tsv)
az identity federated-credential show --name github-main --identity-name "$DEPLOY_IDENTITY" -g "$RESOURCE_GROUP" -o none 2>/dev/null \
  || az identity federated-credential create --name github-main --identity-name "$DEPLOY_IDENTITY" -g "$RESOURCE_GROUP" \
       --issuer https://token.actions.githubusercontent.com \
       --subject "repo:$GITHUB_REPO:ref:refs/heads/main" \
       --audiences api://AzureADTokenExchange -o none
ENVIRONMENT_ID=$(az containerapp env show -n "$ENVIRONMENT" -g "$RESOURCE_GROUP" --query id -o tsv)
assign_role "$DEPLOY_PRINCIPAL_ID" AcrPush "$ACR_ID"
assign_role "$DEPLOY_PRINCIPAL_ID" Reader "$ACR_ID"
assign_role "$DEPLOY_PRINCIPAL_ID" Contributor "$CONTAINER_APP_ID"
assign_role "$DEPLOY_PRINCIPAL_ID" Contributor "$ENVIRONMENT_ID"

step "GitHub repository variables and secret"
gh variable set AZURE_CLIENT_ID --repo "$GITHUB_REPO" --body "$DEPLOY_CLIENT_ID"
gh variable set AZURE_TENANT_ID --repo "$GITHUB_REPO" --body "$TENANT_ID"
gh variable set AZURE_SUBSCRIPTION_ID --repo "$GITHUB_REPO" --body "$SUBSCRIPTION_ID"
gh variable set AZURE_RESOURCE_GROUP --repo "$GITHUB_REPO" --body "$RESOURCE_GROUP"
gh variable set ACR_NAME --repo "$GITHUB_REPO" --body "$ACR_NAME"
gh variable set CONTAINER_APP_NAME --repo "$GITHUB_REPO" --body "$CONTAINER_APP"
gh variable set WHISPER_MODEL --repo "$GITHUB_REPO" --body "$WHISPER_MODEL"
gh variable set VITE_API_BASE_URL --repo "$GITHUB_REPO" --body "https://$BACKEND_HOST"
az staticwebapp secrets list -n "$STATIC_WEB_APP" -g "$RESOURCE_GROUP" --query properties.apiKey -o tsv \
  | gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --repo "$GITHUB_REPO"

cat <<EOF

Done.
  Frontend: https://$FRONTEND_HOST
  Backend:  https://$BACKEND_HOST  (health: https://$BACKEND_HOST/health)

Next: run ./infra/azure-secrets.sh in your own terminal to store the API keys,
database URL and access key, then push to main to trigger the first deployment.
EOF
