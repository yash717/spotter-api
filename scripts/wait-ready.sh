#!/usr/bin/env bash
# scripts/wait-ready.sh
# Polls until all pods in the spotter namespace are Running + Ready.
# Timeout: 3 minutes. Poll interval: 5 seconds.

set -euo pipefail

NAMESPACE="spotter"
TIMEOUT=180   # seconds
INTERVAL=5
ELAPSED=0

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${YELLOW}⏳ Waiting for all pods in namespace '$NAMESPACE' to be Ready...${NC}"
echo "   (timeout: ${TIMEOUT}s)"
echo ""

while true; do
  # Get all pods — name, status, and ready columns
  POD_STATUS_RAW=$(kubectl get pods -n "$NAMESPACE" \
    --no-headers \
    -o custom-columns="NAME:.metadata.name,STATUS:.status.phase,READY:.status.containerStatuses[*].ready" \
    2>/dev/null || echo "")

  if [[ -z "$POD_STATUS_RAW" ]]; then
    echo -e "  ${YELLOW}⏳ No pods found yet... (${ELAPSED}s elapsed)${NC}"
  else
    ALL_READY=true
    NOT_READY_PODS=()

    while IFS= read -r line; do
      POD_NAME=$(echo "$line" | awk '{print $1}')
      POD_PHASE=$(echo "$line" | awk '{print $2}')
      POD_READY=$(echo "$line" | awk '{print $3}')

      # A pod is ready when phase=Running and all containers report 'true'
      if [[ "$POD_PHASE" == "Running" && ! "$POD_READY" == *"false"* && -n "$POD_READY" ]]; then
        echo -e "  ${GREEN}✅ $POD_NAME${NC} — Running + Ready"
      else
        echo -e "  ${YELLOW}⏳ $POD_NAME${NC} — Phase: $POD_PHASE | Ready: $POD_READY (${ELAPSED}s elapsed)"
        ALL_READY=false
        NOT_READY_PODS+=("$POD_NAME")
      fi
    done <<< "$POD_STATUS_RAW"

    if $ALL_READY; then
      echo ""
      echo -e "${GREEN}✅ All pods Ready! Cluster is fully operational.${NC}"
      exit 0
    fi
  fi

  if [[ $ELAPSED -ge $TIMEOUT ]]; then
    echo ""
    echo -e "${RED}❌ Timed out after ${TIMEOUT}s waiting for pods to become Ready.${NC}"
    echo ""
    echo "  Debug commands:"
    echo "    make events       → show recent cluster events"
    echo "    make logs-migrate → show Django migration logs"
    echo "    make logs-api     → show API container logs"
    echo ""
    kubectl get pods -n "$NAMESPACE" 2>/dev/null || true
    exit 1
  fi

  echo ""
  sleep "$INTERVAL"
  ELAPSED=$((ELAPSED + INTERVAL))
done
