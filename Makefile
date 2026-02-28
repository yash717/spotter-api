# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Spotter ELD — Local Kubernetes Dev Environment
#  Powered by kind (Kubernetes in Docker)
#
#  ONE COMMAND TO RULE THEM ALL:
#    make up    → spin up cluster from zero
#    make test  → run all 10 automated checks
#    make nuke  → wipe everything clean
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CLUSTER_NAME  := spotter-local
NAMESPACE     := spotter
API_IMAGE     := spotter-api:local
API_PORT      := 8000
K8S_DIR       := k8s
SCRIPTS_DIR   := scripts
PF_PID_FILE   := .pf.pid

# Default kubectl context for kind
KUBECTL := kubectl --context kind-$(CLUSTER_NAME)

.DEFAULT_GOAL := help

# ── Help ──────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  ┌─────────────────────────────────────────────────────────────────┐"
	@echo "  │          Spotter ELD — Local Kubernetes Dev Environment         │"
	@echo "  │                   Cluster: $(CLUSTER_NAME)                        │"
	@echo "  └─────────────────────────────────────────────────────────────────┘"
	@echo ""
	@echo "  ── Cluster Lifecycle ──────────────────────────────────────────────"
	@echo "  make cluster-up       Create kind cluster ($(CLUSTER_NAME))"
	@echo "  make cluster-down     Delete kind cluster entirely"
	@echo "  make cluster-status   Show cluster reachability"
	@echo ""
	@echo "  ── Image Management ───────────────────────────────────────────────"
	@echo "  make build            Build $(API_IMAGE) Docker image"
	@echo "  make load             Load $(API_IMAGE) into kind cluster"
	@echo "  make build-load       Build + load in one step"
	@echo ""
	@echo "  ── Secrets & Config ───────────────────────────────────────────────"
	@echo "  make secrets          Create K8s secrets from .env.k8s"
	@echo "  make secrets-check    Show which secret keys exist in cluster"
	@echo ""
	@echo "  ── Deploy ─────────────────────────────────────────────────────────"
	@echo "  make apply            kubectl apply all manifests in k8s/ directory"
	@echo "  make wait             Block until all pods are Running + Ready"
	@echo "  make up               Full one-shot: cluster + images + secrets + deploy"
	@echo ""
	@echo "  ── Observe ────────────────────────────────────────────────────────"
	@echo "  make status           Show pods, services, pvc, endpoints"
	@echo "  make logs-api         Tail spotter-api container logs"
	@echo "  make logs-postgres    Tail spotter-postgres container logs"
	@echo "  make logs-migrate     Show logs from migrate initContainer"
	@echo "  make events           Show cluster events sorted by time"
	@echo ""
	@echo "  ── Interact ───────────────────────────────────────────────────────"
	@echo "  make forward          Port-forward API to localhost:$(API_PORT) (foreground)"
	@echo "  make forward-bg       Port-forward in background (saves PID)"
	@echo "  make forward-stop     Kill background port-forward"
	@echo "  make shell-api        Exec shell into spotter-api pod"
	@echo "  make shell-postgres   Open psql inside postgres pod"
	@echo "  make django-shell     Run python manage.py shell in api pod"
	@echo ""
	@echo "  ── Test ───────────────────────────────────────────────────────────"
	@echo "  make test             Run all 10 automated health checks"
	@echo "  make test-db          Quick DB connectivity check only"
	@echo "  make test-api         Port-forward + curl health + assert 200"
	@echo ""
	@echo "  ── Data ───────────────────────────────────────────────────────────"
	@echo "  make seed             Run seed_dev_data management command in API pod"
	@echo "  make seed-print       Print all seeded data from PostgreSQL"
	@echo "  make supabase-check   Show Supabase config status in UI ConfigMap"
	@echo ""
	@echo "  ── Teardown ───────────────────────────────────────────────────────"
	@echo "  make down             Delete kind cluster (non-interactive, for scripts)"
	@echo "  make clean            Remove temp files (.pf.pid etc.)"
	@echo "  make nuke             Confirmation prompt → full wipe → back to zero"
	@echo ""

# ── Cluster Lifecycle ─────────────────────────────────────────────────────────
.PHONY: cluster-up
cluster-up:
	@echo "🚀 Creating kind cluster '$(CLUSTER_NAME)'..."
	@kind get clusters 2>/dev/null | grep -q "^$(CLUSTER_NAME)$$" && \
	  echo "   ℹ️  Cluster '$(CLUSTER_NAME)' already exists — skipping creation." || \
	  kind create cluster --config $(K8S_DIR)/kind-config.yaml
	@echo "✅ Cluster ready."

.PHONY: cluster-down
cluster-down:
	@echo "🗑  Deleting kind cluster '$(CLUSTER_NAME)'..."
	@kind delete cluster --name $(CLUSTER_NAME) 2>/dev/null || echo "   (cluster not found, nothing to delete)"
	@echo "✅ Cluster deleted."

.PHONY: cluster-status
cluster-status:
	@echo "── Kind Clusters ──────────────────────────────────"
	@kind get clusters 2>/dev/null || echo "(none)"
	@echo ""
	@echo "── Kubectl Context ────────────────────────────────"
	@$(KUBECTL) cluster-info 2>&1 | head -5 || echo "(not reachable)"

# ── Image Management ──────────────────────────────────────────────────────────
.PHONY: build
build:
	@echo "🔨 Building Docker image $(API_IMAGE)..."
	@DOCKER_BUILDKIT=1 docker build --network host -t $(API_IMAGE) .
	@echo "✅ Image $(API_IMAGE) built."

.PHONY: load
load:
	@echo "📦 Loading $(API_IMAGE) into kind cluster '$(CLUSTER_NAME)'..."
	@kind load docker-image $(API_IMAGE) --name $(CLUSTER_NAME)
	@echo "✅ Image loaded."

.PHONY: build-load
build-load: build load

# ── Secrets & Config ──────────────────────────────────────────────────────────
.PHONY: secrets
secrets:
	@echo "🔐 Creating/updating K8s secrets from .env.k8s..."
	@bash $(SCRIPTS_DIR)/create-secrets.sh

.PHONY: secrets-check
secrets-check:
	@echo "── Secret: spotter-api-secrets ────────────────────"
	@$(KUBECTL) get secret spotter-api-secrets -n $(NAMESPACE) \
	  -o jsonpath='{.data}' 2>/dev/null | python3 -c \
	  "import sys,json; d=json.load(sys.stdin); [print('  •', k) for k in sorted(d.keys())]" \
	  || echo "  (not found)"
	@echo ""
	@echo "── Secret: spotter-postgres-secret ────────────────"
	@$(KUBECTL) get secret spotter-postgres-secret -n $(NAMESPACE) \
	  -o jsonpath='{.data}' 2>/dev/null | python3 -c \
	  "import sys,json; d=json.load(sys.stdin); [print('  •', k) for k in sorted(d.keys())]" \
	  || echo "  (not found)"

# ── Deploy ────────────────────────────────────────────────────────────────────
.PHONY: apply
apply:
	@echo "📋 Applying Kubernetes manifests (ordered)..."
	@$(KUBECTL) apply -f $(K8S_DIR)/namespace.yaml
	@$(KUBECTL) apply -f $(K8S_DIR)/secret.yaml       2>/dev/null || true
	@$(KUBECTL) apply -f $(K8S_DIR)/configmap.yaml
	@$(KUBECTL) apply -f $(K8S_DIR)/postgres-deployment.yaml
	@echo "   ⏳ Waiting 8s for postgres to initialise before applying API..."
	@sleep 8
	@$(KUBECTL) apply -f $(K8S_DIR)/api-deployment.yaml
	@echo "✅ All manifests applied."

.PHONY: wait
wait:
	@echo "⏳ Waiting for all pods to be Ready..."
	@bash $(SCRIPTS_DIR)/wait-ready.sh

.PHONY: up
up:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════╗"
	@echo "║      Spotter ELD — Full Local K8s Cluster Spin-Up   ║"
	@echo "╚══════════════════════════════════════════════════════╝"
	@echo ""
	@$(MAKE) cluster-up
	@$(MAKE) build-load
	@$(MAKE) secrets
	@$(MAKE) apply
	@$(MAKE) wait
	@echo ""
	@echo "╔══════════════════════════════════════════════════════╗"
	@echo "║   ✅ Cluster is UP and READY                         ║"
	@echo "║                                                      ║"
	@echo "║   make test       → run automated checks             ║"
	@echo "║   make forward    → port-forward API to :8000        ║"
	@echo "║   make nuke       → wipe everything when done        ║"
	@echo "╚══════════════════════════════════════════════════════╝"
	@echo ""

# ── Observe ───────────────────────────────────────────────────────────────────
.PHONY: status
status:
	@echo "── Pods ───────────────────────────────────────────────"
	@$(KUBECTL) get pods -n $(NAMESPACE) -o wide
	@echo ""
	@echo "── Services ───────────────────────────────────────────"
	@$(KUBECTL) get svc -n $(NAMESPACE)
	@echo ""
	@echo "── PersistentVolumeClaims ─────────────────────────────"
	@$(KUBECTL) get pvc -n $(NAMESPACE)
	@echo ""
	@echo "── Endpoints ──────────────────────────────────────────"
	@$(KUBECTL) get endpoints -n $(NAMESPACE)

.PHONY: logs-api
logs-api:
	@API_POD=$$($(KUBECTL) get pod -l app=spotter-api -n $(NAMESPACE) \
	  --no-headers -o custom-columns="NAME:.metadata.name" | head -1); \
	echo "📜 Tailing logs for pod: $$API_POD"; \
	$(KUBECTL) logs -f "$$API_POD" -c spotter-api -n $(NAMESPACE)

.PHONY: logs-postgres
logs-postgres:
	@PG_POD=$$($(KUBECTL) get pod -l app=spotter-postgres -n $(NAMESPACE) \
	  --no-headers -o custom-columns="NAME:.metadata.name" | head -1); \
	echo "📜 Tailing logs for pod: $$PG_POD"; \
	$(KUBECTL) logs -f "$$PG_POD" -n $(NAMESPACE)

.PHONY: logs-migrate
logs-migrate:
	@API_POD=$$($(KUBECTL) get pod -l app=spotter-api -n $(NAMESPACE) \
	  --no-headers -o custom-columns="NAME:.metadata.name" | head -1); \
	echo "📜 Migration initContainer logs for pod: $$API_POD"; \
	$(KUBECTL) logs "$$API_POD" -c migrate -n $(NAMESPACE)

.PHONY: events
events:
	@echo "── Cluster Events (sorted by time) ────────────────────"
	@$(KUBECTL) get events -n $(NAMESPACE) --sort-by='.lastTimestamp'

# ── Interact ──────────────────────────────────────────────────────────────────
.PHONY: forward
forward:
	@echo "🔗 Port-forwarding spotter-api → localhost:$(API_PORT) (Ctrl+C to stop)"
	@$(KUBECTL) port-forward svc/spotter-api $(API_PORT):8000 -n $(NAMESPACE)

.PHONY: forward-bg
forward-bg:
	@echo "🔗 Starting background port-forward → localhost:$(API_PORT)"
	@$(KUBECTL) port-forward svc/spotter-api $(API_PORT):8000 -n $(NAMESPACE) &>/dev/null & \
	echo $$! > $(PF_PID_FILE)
	@sleep 2
	@echo "✅ Port-forward running (PID: $$(cat $(PF_PID_FILE))). Stop with: make forward-stop"

.PHONY: forward-stop
forward-stop:
	@if [ -f $(PF_PID_FILE) ]; then \
	  PID=$$(cat $(PF_PID_FILE)); \
	  kill $$PID 2>/dev/null && echo "✅ Port-forward (PID $$PID) stopped." || echo "Process $$PID not found."; \
	  rm -f $(PF_PID_FILE); \
	else \
	  echo "No PID file found ($(PF_PID_FILE)). Nothing to stop."; \
	fi

.PHONY: shell-api
shell-api:
	@API_POD=$$($(KUBECTL) get pod -l app=spotter-api -n $(NAMESPACE) \
	  --no-headers -o custom-columns="NAME:.metadata.name" | head -1); \
	echo "🐚 Exec into $$API_POD..."; \
	$(KUBECTL) exec -it "$$API_POD" -n $(NAMESPACE) -- /bin/sh

.PHONY: shell-postgres
shell-postgres:
	@PG_POD=$$($(KUBECTL) get pod -l app=spotter-postgres -n $(NAMESPACE) \
	  --no-headers -o custom-columns="NAME:.metadata.name" | head -1); \
	echo "🐘 Opening psql in $$PG_POD..."; \
	$(KUBECTL) exec -it "$$PG_POD" -n $(NAMESPACE) -- \
	  psql -U spotter -d spotter_k8s

.PHONY: django-shell
django-shell:
	@API_POD=$$($(KUBECTL) get pod -l app=spotter-api -n $(NAMESPACE) \
	  --no-headers -o custom-columns="NAME:.metadata.name" | head -1); \
	echo "🐍 Django shell in $$API_POD..."; \
	$(KUBECTL) exec -it "$$API_POD" -n $(NAMESPACE) -- \
	  python manage.py shell

# ── Test ──────────────────────────────────────────────────────────────────────
.PHONY: test
test:
	@bash $(SCRIPTS_DIR)/health-check.sh

.PHONY: test-db
test-db:
	@PG_POD=$$($(KUBECTL) get pod -l app=spotter-postgres -n $(NAMESPACE) \
	  --no-headers -o custom-columns="NAME:.metadata.name" | head -1); \
	echo "🔎 DB ping: pg_isready inside $$PG_POD"; \
	$(KUBECTL) exec "$$PG_POD" -n $(NAMESPACE) -- \
	  pg_isready -U spotter -d spotter_k8s && echo "✅ DB is accepting connections" \
	  || echo "❌ DB not ready"

.PHONY: test-api
test-api:
	@echo "🔎 Testing API health endpoint..."
	@$(KUBECTL) port-forward svc/spotter-api $(API_PORT):8000 -n $(NAMESPACE) &>/dev/null & \
	PF_PID=$$!; sleep 3; \
	HTTP_CODE=$$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
	  http://localhost:$(API_PORT)/api/v1/health/ 2>/dev/null || echo "000"); \
	kill $$PF_PID 2>/dev/null || true; \
	if [ "$$HTTP_CODE" = "200" ]; then \
	  echo "✅ PASS — GET /api/v1/health/ returned HTTP $$HTTP_CODE"; \
	else \
	  echo "❌ FAIL — Expected 200, got HTTP $$HTTP_CODE"; exit 1; \
	fi

# ── Data ──────────────────────────────────────────────────────────────────────
.PHONY: seed
seed:
	@API_POD=$$($(KUBECTL) get pod -l app=spotter-api -n $(NAMESPACE) \
	  --no-headers -o custom-columns="NAME:.metadata.name" | head -1); \
	echo "🌱 Running seed_dev_data in pod: $$API_POD"; \
	$(KUBECTL) exec "$$API_POD" -n $(NAMESPACE) -- python manage.py seed_dev_data

.PHONY: seed-print
seed-print:
	@PG_POD=$$($(KUBECTL) get pod -l app=spotter-postgres -n $(NAMESPACE) \
	  --no-headers -o custom-columns="NAME:.metadata.name" | head -1); \
	echo ""; \
	echo "── ORGANIZATIONS ──────────────────────────────────────"; \
	$(KUBECTL) exec "$$PG_POD" -n $(NAMESPACE) -- \
	  psql -U spotter -d spotter_k8s -c \
	  "SELECT name, dot_number, mc_number, phone FROM organizations ORDER BY name;" ; \
	echo ""; \
	echo "── USERS ──────────────────────────────────────────────"; \
	$(KUBECTL) exec "$$PG_POD" -n $(NAMESPACE) -- \
	  psql -U spotter -d spotter_k8s -c \
	  "SELECT email, first_name, last_name, is_superuser FROM users ORDER BY is_superuser DESC, email;" ; \
	echo ""; \
	echo "── MEMBERS BY ROLE ────────────────────────────────────"; \
	$(KUBECTL) exec "$$PG_POD" -n $(NAMESPACE) -- \
	  psql -U spotter -d spotter_k8s -c \
	  "SELECT role, count(*) FROM organization_members GROUP BY role ORDER BY count DESC;" ; \
	echo ""; \
	echo "── VEHICLES ───────────────────────────────────────────"; \
	$(KUBECTL) exec "$$PG_POD" -n $(NAMESPACE) -- \
	  psql -U spotter -d spotter_k8s -c \
	  "SELECT truck_number, trailer_number, license_plate, odometer_current FROM vehicles ORDER BY truck_number;" ; \
	echo ""; \
	echo "── TRIPS ──────────────────────────────────────────────"; \
	$(KUBECTL) exec "$$PG_POD" -n $(NAMESPACE) -- \
	  psql -U spotter -d spotter_k8s -c \
	  "SELECT status, input_current_address, input_dropoff_address, total_trip_distance_miles FROM trips ORDER BY status;" ; \
	echo ""; \
	echo "── INVITATIONS ────────────────────────────────────────"; \
	$(KUBECTL) exec "$$PG_POD" -n $(NAMESPACE) -- \
	  psql -U spotter -d spotter_k8s -c \
	  "SELECT email, role, status, expires_at FROM invitations;" ; \
	echo ""; \
	echo "── AUDIT LOGS ─────────────────────────────────────────"; \
	$(KUBECTL) exec "$$PG_POD" -n $(NAMESPACE) -- \
	  psql -U spotter -d spotter_k8s -c \
	  "SELECT action, created_at FROM audit_logs ORDER BY created_at;"

.PHONY: supabase-check
supabase-check:
	@echo "── Supabase Config Status ──────────────────────────────"
	@echo ""
	@echo "  The Spotter-ui uses Supabase as an optional integration."
	@echo "  It is NULL-SAFE: if env vars are empty, supabase client = null."
	@echo "  The app works fully without Supabase configured."
	@echo ""
	@SUPABASE_URL=$$($(KUBECTL) get configmap spotter-ui-config -n $(NAMESPACE) \
	  -o jsonpath='{.data.NEXT_PUBLIC_SUPABASE_URL}' 2>/dev/null || echo ""); \
	if [ -z "$$SUPABASE_URL" ]; then \
	  echo "  Status: ⚠️  NOT configured (NEXT_PUBLIC_SUPABASE_URL not set in ConfigMap)"; \
	  echo "  Impact: Supabase features disabled — Django API is the primary backend."; \
	else \
	  echo "  Status: ✅ Configured — URL: $$SUPABASE_URL"; \
	fi
	@echo ""
	@echo "  To enable: add NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY"
	@echo "  to Spotter-ui/k8s/ui-deployment.yaml and run: make apply"

# ── Teardown ──────────────────────────────────────────────────────────────────
.PHONY: down
down: cluster-down

.PHONY: clean
clean:
	@rm -f $(PF_PID_FILE)
	@echo "✅ Temp files cleaned."

.PHONY: nuke
nuke:
	@bash $(SCRIPTS_DIR)/teardown-confirm.sh
	@$(MAKE) clean
