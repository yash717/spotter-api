import dj_database_url

from .base import *  # noqa: F401,F403

DEBUG = True

DATABASE_URL = config("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

# Email: use Brevo if SMTP_* set, else console
if config("SMTP_USER", default=""):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = config("SMTP_HOST", default="smtp-relay.brevo.com")
    EMAIL_PORT = config("SMTP_PORT", default=587, cast=int)
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = config("SMTP_USER")
    EMAIL_HOST_PASSWORD = config("SMTP_PASS")
    DEFAULT_FROM_EMAIL = config(
        "SMTP_FROM_EMAIL", config("EMAIL_FROM", default="noreply@spotter.ai")
    )
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "noreply@spotter-dev.local"

# Allow browsable API in dev
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
