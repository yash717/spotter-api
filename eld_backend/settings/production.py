from decouple import Csv, config

from .base import *  # noqa: F401,F403

import dj_database_url

DEBUG = False

# Enable WhiteNoise to serve static files in production
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,.onrender.com",
    cast=Csv(),
)

# Support DATABASE_URL (Render auto-sets this) or individual DB vars
_database_url = config("DATABASE_URL", default="")
if _database_url:
    DATABASES = {"default": dj_database_url.parse(_database_url)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="eld_db"),
            "USER": config("DB_USER", default="eld_user"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="https://spotter-ui-ashy.vercel.app",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

# Required for Django 4.0+ CSRF when serving over HTTPS (admin login, form submissions)
# Include the API's own origin and frontend origins
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://spotter-api-ld45.onrender.com,https://spotter-ui-ashy.vercel.app",
    cast=Csv(),
)

# Email: Brevo API (recommended on Render - SMTP ports are blocked on free tier)
# Fallback to SMTP for paid Render or local dev
if config("BREVO_API_KEY", default=""):
    # Brevo REST API uses HTTPS - works on Render free tier
    EMAIL_BACKEND = "eld_backend.email_backends.BrevoAPIEmailBackend"
    BREVO_API_KEY = config("BREVO_API_KEY")
    DEFAULT_FROM_EMAIL = config(
        "SMTP_FROM_EMAIL", config("EMAIL_FROM", default="noreply@spotter.ai")
    )
elif config("SMTP_USER", default=""):
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
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.sendgrid.net"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = "apikey"
    EMAIL_HOST_PASSWORD = config("SENDGRID_API_KEY", default="")
    DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@spotter.ai")

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
