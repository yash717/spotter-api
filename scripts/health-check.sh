#!/usr/bin/env bash
# scripts/health-check.sh
# Full automated local test suite for the Spotter ELD k8s deployment.
# Each check prints PASS or FAIL. Final summary: X/Y checks passed.
# Exit 0 only if all checks pass.

set -euo pipefail

NAMESPACE="spotter"
CLUSTER_NAME="spotter-local"
API_LOCAL_PORT="8000"
PF_PID_FILE="/tmp/spotter-hc-pf.pid"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'

PASS=0
FAIL=0
TOTAL=10

pass() { echo -e "  ${GREEN}✅ PASS${NC} — $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}❌ FAIL${NC} — $1"; FAIL=$((FAIL + 1)); }

header() {
  echo ""
  echo -e "${BOLD}[$1/$TOTAL] $2${NC}"
}

cleanup_pf() {
  if [[ -f "$PF_PID_FILE" ]]; then
    local pid
    pid=$(cat "$PF_PID_FILE")
    kill "$pid" 2>/dev/null || true
    rm -f "$PF_PID_FILE"
  fi
}
trap cleanup_pf EXIT

echo ""
echo -e "${BOLD}════════════════════════════════════════════════${NC}"
echo -e "${BOLD}   Spotter ELD — Kubernetes Health Check Suite  ${NC}"
echo -e "${BOLD}════════════════════════════════════════════════${NC}"

# ── Check 1: Kind cluster exists ─────────────────────────────────────────────
header 1 "KIND CLUSTER"
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  pass "kind cluster '$CLUSTER_NAME' exists"
else
  fail "kind cluster '$CLUSTER_NAME' not found — run: make cluster-up"
fi

# ── Check 2: Namespace exists ────────────────────────────────────────────────
header 2 "NAMESPACE"
if kubectl get namespace "$NAMESPACE" --no-headers 2>/dev/null | grep -q "Active"; then
  pass "namespace '$NAMESPACE' exists and is Active"
else
  fail "namespace '$NAMESPACE' not found — run: make apply"
fi

# ── Check 3: PVC is Bound ────────────────────────────────────────────────────
header 3 "PVC BOUND"
PVC_STATUS=$(kubectl get pvc postgres-pvc -n "$NAMESPACE" \
  --no-headers -o custom-columns="STATUS:.status.phase" 2>/dev/null || echo "NOT_FOUND")
if [[ "$PVC_STATUS" == "Bound" ]]; then
  pass "PVC 'postgres-pvc' is Bound"
else
  fail "PVC 'postgres-pvc' status: $PVC_STATUS (expected: Bound)"
fi

# ── Check 4: Postgres pod is Running + Ready ────────────────────────────────
header 4 "POSTGRES RUNNING"
PG_READY=$(kubectl get pod -l app=spotter-postgres -n "$NAMESPACE" \
  --no-headers -o custom-columns="STATUS:.status.phase,READY:.status.containerStatuses[*].ready" \
  2>/dev/null || echo "")
if echo "$PG_READY" | grep -q "Running.*true"; then
  pass "spotter-postgres pod is Running and Ready"
else
  PG_STATUS="${PG_READY:-not found}"
  fail "spotter-postgres not Ready: $PG_STATUS"
fi

# ── Check 5: Postgres pg_isready ────────────────────────────────────────────
header 5 "POSTGRES PING"
PG_POD=$(kubectl get pod -l app=spotter-postgres -n "$NAMESPACE" \
  --no-headers -o custom-columns="NAME:.metadata.name" 2>/dev/null | head -1 || echo "")
if [[ -n "$PG_POD" ]]; then
  PG_PING=$(kubectl exec "$PG_POD" -n "$NAMESPACE" -- \
    pg_isready -U spotter -d spotter_k8s 2>&1 || echo "FAILED")
  if echo "$PG_PING" | grep -q "accepting connections"; then
    pass "PostgreSQL is accepting connections (pg_isready OK)"
  else
    fail "pg_isready failed: $PG_PING"
  fi
else
  fail "Cannot find postgres pod to ping"
fi

# ── Check 6: Migration initContainer logs ───────────────────────────────────
header 6 "MIGRATE DONE"
API_POD=$(kubectl get pod -l app=spotter-api -n "$NAMESPACE" \
  --no-headers -o custom-columns="NAME:.metadata.name" 2>/dev/null | head -1 || echo "")
if [[ -n "$API_POD" ]]; then
  MIGRATE_LOGS=$(kubectl logs "$API_POD" -c migrate -n "$NAMESPACE" 2>&1 || echo "")
  if echo "$MIGRATE_LOGS" | grep -qE "(Applying|No migrations to apply|OK)"; then
    if echo "$MIGRATE_LOGS" | grep -q "Traceback"; then
      fail "Migration logs contain a Traceback — check: make logs-migrate"
    else
      pass "Django migrations completed successfully"
    fi
  else
    fail "Migration output unexpected: ${MIGRATE_LOGS:0:200}"
  fi
else
  fail "Cannot find spotter-api pod to check migration logs"
fi

# ── Check 7: API pod Running + Ready ────────────────────────────────────────
header 7 "API RUNNING"
API_READY=$(kubectl get pod -l app=spotter-api -n "$NAMESPACE" \
  --no-headers -o custom-columns="STATUS:.status.phase,READY:.status.containerStatuses[*].ready" \
  2>/dev/null || echo "")
if echo "$API_READY" | grep -q "Running.*true"; then
  pass "spotter-api pod is Running and Ready"
else
  API_STATUS="${API_READY:-not found}"
  fail "spotter-api not Ready: $API_STATUS"
fi

# ── Check 8: API health HTTP 200 ────────────────────────────────────────────
header 8 "API HEALTH HTTP"
# Start port-forward in background
kubectl port-forward svc/spotter-api "$API_LOCAL_PORT":8000 -n "$NAMESPACE" &>/dev/null &
PF_PID=$!
echo "$PF_PID" > "$PF_PID_FILE"
sleep 3   # give port-forward time to connect

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time 10 "http://localhost:${API_LOCAL_PORT}/api/v1/health/" 2>/dev/null || echo "000")

kill "$PF_PID" 2>/dev/null || true
rm -f "$PF_PID_FILE"

if [[ "$HTTP_CODE" == "200" ]]; then
  pass "GET /api/v1/health/ returned HTTP $HTTP_CODE"
else
  fail "GET /api/v1/health/ returned HTTP $HTTP_CODE (expected 200)"
fi

# ── Check 9: django_migrations table exists in DB ───────────────────────────
header 9 "DB TABLE CHECK"
if [[ -n "$PG_POD" ]]; then
  TABLE_CHECK=$(kubectl exec "$PG_POD" -n "$NAMESPACE" -- \
    psql -U spotter -d spotter_k8s -tAc \
    "SELECT 1 FROM information_schema.tables WHERE table_name='django_migrations';" \
    2>&1 || echo "")
  if echo "$TABLE_CHECK" | grep -q "^1$"; then
    pass "django_migrations table exists in PostgreSQL (migrations ran successfully)"
  else
    fail "django_migrations table NOT found — migrations may not have run"
  fi
else
  fail "Cannot find postgres pod to check tables"
fi

# ── Check 10: Both secrets exist ────────────────────────────────────────────
header 10 "SECRET EXISTS"
S1=$(kubectl get secret spotter-api-secrets -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l | tr -d ' ')
S2=$(kubectl get secret spotter-postgres-secret -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l | tr -d ' ')
if [[ "$S1" == "1" && "$S2" == "1" ]]; then
  pass "Both secrets exist: spotter-api-secrets + spotter-postgres-secret"
else
  fail "Missing secret(s) — S1:$S1 S2:$S2. Run: make secrets"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════${NC}"
if [[ $FAIL -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}   ✅ ALL CHECKS PASSED: ${PASS}/${TOTAL}${NC}"
  echo -e "${BOLD}════════════════════════════════════════════════${NC}"
  echo ""
  echo -e "  Your Spotter ELD cluster is ${GREEN}fully operational${NC}."
  echo "  API:      kubectl port-forward svc/spotter-api 8000:8000 -n spotter"
  echo "  Console:  make shell-api"
  echo "  Cleanup:  make nuke"
  echo ""
  exit 0
else
  echo -e "${RED}${BOLD}   ❌ ${FAIL} CHECK(S) FAILED: ${PASS}/${TOTAL} passed${NC}"
  echo -e "${BOLD}════════════════════════════════════════════════${NC}"
  echo ""
  echo "  Debug:"
  echo "    make events       → cluster events"
  echo "    make logs-migrate → initContainer migration logs"
  echo "    make logs-api     → API container logs"
  echo "    make status       → pod/svc overview"
  echo ""
  exit 1
fi
