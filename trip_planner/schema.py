"""
drf-spectacular extensions for custom authentication and enum naming.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


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
