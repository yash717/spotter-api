#!/usr/bin/env bash
# scripts/teardown-confirm.sh
# Safety wrapper around cluster deletion.
# Called by `make nuke` — requires explicit "YES" confirmation.

set -euo pipefail

CLUSTER_NAME="spotter-local"
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; BOLD='\033[1m'; NC='\033[0m'

echo ""
echo -e "${RED}${BOLD}⚠️  WARNING: Destructive Operation${NC}"
echo ""
echo -e "  This will ${RED}DELETE${NC} the kind cluster '${BOLD}${CLUSTER_NAME}${NC}' and ALL data inside it."
echo ""
echo -e "  The following will be ${RED}permanently destroyed${NC}:"
echo "    • All running pods (spotter-api, spotter-postgres)"
echo "    • All Kubernetes secrets (spotter-api-secrets, spotter-postgres-secret)"
echo "    • All PersistentVolumes and PersistentVolumeClaims (postgres data)"
echo "    • All ConfigMaps, Services, Deployments in the spotter namespace"
echo "    • The kind control-plane container itself"
echo ""
echo -e "  ${GREEN}NOT affected:${NC}"
echo "    • Your local Docker images (spotter-api:local, spotter-ui:local)"
echo "    • Your .env.k8s file"
echo "    • Your source code"
echo ""
echo -e "${YELLOW}To rebuild from scratch: run 'make up' again.${NC}"
echo ""

printf "Are you sure? Type YES to confirm: "
read -r CONFIRM

if [[ "$CONFIRM" == "YES" ]]; then
  echo ""
  echo -e "${YELLOW}🗑  Deleting kind cluster '$CLUSTER_NAME'...${NC}"
  kind delete cluster --name "$CLUSTER_NAME"
  echo ""
  echo -e "${GREEN}✅ Cluster '${CLUSTER_NAME}' deleted. Your machine is clean.${NC}"
  echo ""
  echo "  To start fresh: make up"
else
  echo ""
  echo "Aborted. Cluster '$CLUSTER_NAME' was NOT deleted."
  exit 0
fi
