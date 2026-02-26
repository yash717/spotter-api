from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from trip_planner.models import OrganizationMember


def assert_active_membership(user):
    """Reject deactivated members immediately; no token validity grace period."""
    if getattr(user, "is_superuser", False):
        return
    has_active = OrganizationMember.objects.filter(
        user=user, is_active=True
    ).exists()
    if has_active:
        return
    has_any = OrganizationMember.objects.filter(user=user).exists()
    if has_any:
        raise InvalidToken(
            "Account has been deactivated. Please contact your administrator."
        )


class CookieJWTAuthentication(JWTAuthentication):
    """
    [F3] Reads JWT access token from httpOnly cookie first.
    Falls back to Authorization: Bearer <token> header (for Swagger testing).
    Rejects deactivated members immediately (no 15-min token validity window).
    Returns None (unauthenticated) for invalid/expired tokens so AllowAny views
    (login, register) can proceed without 401 when stale cookies exist.
    """

    def authenticate(self, request):
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return super().authenticate(request)
        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            assert_active_membership(user)
            return user, validated_token
        except (InvalidToken, TokenError, AuthenticationFailed):
            return None
