#!/usr/bin/env bash
# scripts/create-secrets.sh
# Reads .env.k8s and creates/updates Kubernetes secrets in the spotter namespace.
# Uses --dry-run=client | kubectl apply — fully idempotent (safe to re-run).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/.env.k8s"
NAMESPACE="spotter"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ── Guard: .env.k8s must exist ────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
  echo -e "${RED}ERROR: .env.k8s not found at $ENV_FILE${NC}"
  echo ""
  echo "  To fix:"
  echo "    cp $ROOT_DIR/.env.k8s.example $ROOT_DIR/.env.k8s"
  echo "    # then edit .env.k8s with your real values"
  exit 1
fi

echo -e "${YELLOW}📋 Reading secrets from $ENV_FILE${NC}"

# ── Helper: load a specific key from .env.k8s ────────────────────────────────
get_env() {
  local key="$1"
  local default="${2:-}"
  local val
  val=$(grep -E "^${key}=" "$ENV_FILE" | cut -d= -f2- | tr -d '\r' || true)
  if [[ -z "$val" && -z "$default" ]]; then
    echo -e "${RED}ERROR: Required key '$key' missing from .env.k8s${NC}" >&2
    exit 1
  fi
  echo "${val:-$default}"
}

# ── Read all values ───────────────────────────────────────────────────────────
POSTGRES_USER=$(get_env "POSTGRES_USER")
POSTGRES_PASSWORD=$(get_env "POSTGRES_PASSWORD")
POSTGRES_DB=$(get_env "POSTGRES_DB")
SECRET_KEY=$(get_env "SECRET_KEY")
INVITATION_JWT_SECRET=$(get_env "INVITATION_JWT_SECRET")
DB_PASSWORD=$(get_env "DB_PASSWORD")
SMTP_USER=$(get_env "SMTP_USER" "")
SMTP_PASS=$(get_env "SMTP_PASS" "")
SMTP_FROM_EMAIL=$(get_env "SMTP_FROM_EMAIL" "noreply@spotter.ai")
EMAIL_FROM=$(get_env "EMAIL_FROM" "noreply@spotter.ai")
ORS_API_KEY=$(get_env "ORS_API_KEY" "")

# ── Ensure namespace exists ───────────────────────────────────────────────────
kubectl get namespace "$NAMESPACE" &>/dev/null || \
  kubectl create namespace "$NAMESPACE"

# ── Secret 1: spotter-postgres-secret ────────────────────────────────────────
kubectl create secret generic spotter-postgres-secret \
  --namespace="$NAMESPACE" \
  --from-literal=POSTGRES_USER="$POSTGRES_USER" \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=POSTGRES_DB="$POSTGRES_DB" \
  --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}✅ Created/Updated secret: spotter-postgres-secret${NC}"

# ── Secret 2: spotter-api-secrets ────────────────────────────────────────────
kubectl create secret generic spotter-api-secrets \
  --namespace="$NAMESPACE" \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=INVITATION_JWT_SECRET="$INVITATION_JWT_SECRET" \
  --from-literal=DB_PASSWORD="$DB_PASSWORD" \
  --from-literal=SMTP_USER="$SMTP_USER" \
  --from-literal=SMTP_PASS="$SMTP_PASS" \
  --from-literal=SMTP_FROM_EMAIL="$SMTP_FROM_EMAIL" \
  --from-literal=EMAIL_FROM="$EMAIL_FROM" \
  --from-literal=ORS_API_KEY="$ORS_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}✅ Created/Updated secret: spotter-api-secrets${NC}"
echo ""
echo -e "${GREEN}🔐 All secrets applied to namespace '$NAMESPACE'${NC}"
