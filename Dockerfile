# ─── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# System deps needed to compile psycopg2 etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# ─── Stage 2: Runner ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=eld_backend.settings.production \
    PORT=8000

WORKDIR /app

# Runtime OS deps only (libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Collect static files (needs a dummy SECRET_KEY at build time)
RUN SECRET_KEY=build-time-placeholder \
    INVITATION_JWT_SECRET=build-time-placeholder \
    DB_HOST=localhost \
    DB_NAME=dummy \
    DB_USER=dummy \
    DB_PASSWORD=dummy \
    python manage.py collectstatic --noinput --clear 2>/dev/null || true

# Create non-root user for security
RUN addgroup --system spotter && adduser --system --ingroup spotter spotter
RUN chown -R spotter:spotter /app
USER spotter

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

# Run Daphne (ASGI server — supports HTTP + WebSockets)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "eld_backend.asgi:application"]
