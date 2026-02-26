from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")
INVITATION_JWT_SECRET = config("INVITATION_JWT_SECRET")
INVITATION_JWT_ALGORITHM = "HS256"

FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")

INSTALLED_APPS = [
    "daphne",
    "channels",
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # Local
    "trip_planner",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "eld_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "eld_backend.wsgi.application"
ASGI_APPLICATION = "eld_backend.asgi.application"

# Channels - use in-memory layer for dev (no Redis required)
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "trip_planner.User"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "trip_planner.authentication.CookieJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "trip_planner.pagination.SpotterPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# --- drf-spectacular (Swagger / OpenAPI) ---
SPECTACULAR_SETTINGS = {
    "TITLE": "Spotter AI — ELD Trip Planner API",
    "DESCRIPTION": (
        "REST API for the Spotter AI ELD Trip Planner v2.\n\n"
        "Covers organization management, role-based invitation system, "
        "fleet management, HOS-compliant trip planning, and ELD log generation.\n\n"
        "**Authentication:** httpOnly cookie-based JWT. "
        "Login via `POST /api/v1/auth/login/` to receive cookies automatically.\n\n"
        "For Swagger testing, use the **Authorize** button (top-right) and paste a raw JWT token."
    ),
    "VERSION": "1.0.0",
    "CONTACT": {"name": "Spotter AI", "email": "support@spotter.ai"},
    "LICENSE": {"name": "Proprietary"},
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "COMPONENT_SPLIT_REQUEST": True,
    "EXTENSIONS_INFO": {},
    "AUTHENTICATION_WHITELIST": [
        "trip_planner.authentication.CookieJWTAuthentication",
    ],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Paste a raw JWT access token here for Swagger testing.",
            },
            "CookieAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "access_token",
                "description": "httpOnly cookie set by /api/v1/auth/login/",
            },
        }
    },
    "SECURITY": [{"BearerAuth": []}, {"CookieAuth": []}],
    "ENUM_NAME_OVERRIDES": {
        "MemberRoleEnum": "trip_planner.constants.MemberRole.CHOICES",
        "InvitationStatusEnum": "trip_planner.constants.InvitationStatus.CHOICES",
        "TripStatusEnum": "trip_planner.constants.TripStatus.CHOICES",
        "StopTypeEnum": "trip_planner.constants.StopType.CHOICES",
        "DutyStatusEnum": "trip_planner.constants.DutyStatus.CHOICES",
        "ViolationTypeEnum": "trip_planner.constants.ViolationType.CHOICES",
        "SeverityEnum": "trip_planner.constants.Severity.CHOICES",
        "AuditActionEnum": "trip_planner.constants.AuditAction.CHOICES",
    },
    "TAGS": [
        {"name": "Auth", "description": "Login, token refresh, logout, session"},
        {"name": "Invitations", "description": "JWT-based email invitation system"},
        {"name": "Organization", "description": "Org settings and member management"},
        {"name": "Vehicles", "description": "Fleet CRUD and driver assignment"},
        {"name": "Trips", "description": "Trip planning, assignment, ELD logs"},
        {"name": "Profile", "description": "Driver profile management"},
    ],
}

# --- SimpleJWT ---
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# --- CORS ---
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# --- Email (Brevo SMTP) ---
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("SMTP_HOST", default="smtp-relay.brevo.com")
EMAIL_PORT = config("SMTP_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("SMTP_USER", default="")
EMAIL_HOST_PASSWORD = config("SMTP_PASS", default="")
DEFAULT_FROM_EMAIL = config("SMTP_FROM_EMAIL", config("EMAIL_FROM", default="noreply@spotter.ai"))

# --- External APIs ---
ORS_API_KEY = config("ORS_API_KEY", default="")
ORS_BASE_URL = "https://api.openrouteservice.org"

# --- Jazzmin Admin Theme ---
JAZZMIN_SETTINGS = {
    "site_title": "Spotter AI Admin",
    "site_header": "Spotter AI",
    "site_brand": "Spotter AI",
    "site_logo": None,
    "login_logo": None,
    "welcome_sign": "Welcome to Spotter AI Administration",
    "copyright": "Spotter AI — ELD Trip Planner",
    "search_model": ["trip_planner.User", "trip_planner.Organization"],
    "topmenu_links": [
        {"name": "API Docs", "url": "/api/docs/", "new_window": True},
        {"app": "trip_planner"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "order_with_respect_to": [
        "trip_planner.Organization",
        "trip_planner.OrganizationMember",
        "trip_planner.Invitation",
        "trip_planner.CustomUser",
        "trip_planner.DriverProfile",
        "trip_planner.Vehicle",
        "trip_planner.Trip",
        "trip_planner.Stop",
        "trip_planner.DailyLogSheet",
        "trip_planner.DutyStatusSegment",
        "trip_planner.HOSViolation",
        "trip_planner.GeocodeCache",
        "trip_planner.AuditLog",
    ],
    "icons": {
        "trip_planner.User": "fas fa-user",
        "trip_planner.Organization": "fas fa-building",
        "trip_planner.OrganizationMember": "fas fa-users",
        "trip_planner.Invitation": "fas fa-envelope-open-text",
        "trip_planner.DriverProfile": "fas fa-id-card",
        "trip_planner.Vehicle": "fas fa-truck",
        "trip_planner.Trip": "fas fa-route",
        "trip_planner.Stop": "fas fa-map-pin",
        "trip_planner.DailyLogSheet": "fas fa-clipboard-list",
        "trip_planner.DutyStatusSegment": "fas fa-chart-bar",
        "trip_planner.HOSViolation": "fas fa-exclamation-triangle",
        "trip_planner.GeocodeCache": "fas fa-map-marked-alt",
        "trip_planner.AuditLog": "fas fa-history",
        "auth.Group": "fas fa-layer-group",
    },
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}
