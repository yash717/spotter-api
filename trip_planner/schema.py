"""
drf-spectacular extensions for custom authentication and enum naming.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers as s


class CookieJWTAuthExtension(OpenApiAuthenticationExtension):
    target_class = "trip_planner.authentication.CookieJWTAuthentication"
    name = "cookieAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "access_token",
            "description": (
                "JWT access token stored in httpOnly cookie. "
                "Login via POST /api/v1/auth/login/ to get cookies automatically, "
                "or paste a raw JWT below for Swagger testing."
            ),
        }


# Reusable OpenAPI schema for paginated list responses (results + pagination object)
PaginationMetaSerializer = inline_serializer(
    name="PaginationMeta",
    fields={
        "count": s.IntegerField(help_text="Total number of items"),
        "page": s.IntegerField(help_text="Current page (1-based)"),
        "page_size": s.IntegerField(help_text="Page size"),
        "next": s.URLField(allow_null=True, help_text="URL to next page"),
        "previous": s.URLField(allow_null=True, help_text="URL to previous page"),
        "has_next": s.BooleanField(help_text="Whether a next page exists"),
        "has_prev": s.BooleanField(help_text="Whether a previous page exists"),
    },
)


def paginated_list_schema(item_serializer_class, name="PaginatedList"):
    """Build OpenAPI schema for { results: [...], pagination: {...} }."""
    return inline_serializer(
        name=name,
        fields={
            "results": item_serializer_class(many=True),
            "pagination": PaginationMetaSerializer,
        },
    )
