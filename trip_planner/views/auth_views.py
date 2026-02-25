"""
Auth views with httpOnly cookie-based JWT [F3].
JWT payload enriched with org_id, role, driver_profile_id.
"""

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from trip_planner.constants import AuditAction, MemberRole
from trip_planner.models import AuditLog, DriverProfile, OrganizationMember
from trip_planner.serializers import LoginSerializer, RegisterSerializer

ACCESS_TOKEN_MAX_AGE = 60 * 15
REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 7
COOKIE_SECURE = not getattr(settings, "DEBUG", True)

SessionResponseSerializer = inline_serializer(
    name="SessionResponse",
    fields={
        "user": inline_serializer(
            name="SessionUser",
            fields={
                "id": s.UUIDField(),
                "email": s.EmailField(),
                "first_name": s.CharField(),
                "last_name": s.CharField(),
            },
        ),
        "role": s.CharField(allow_null=True),
        "org_id": s.UUIDField(allow_null=True),
        "org_name": s.CharField(allow_null=True),
        "driver_profile_id": s.UUIDField(allow_null=True),
        "member_id": s.UUIDField(allow_null=True),
    },
)
DetailSerializer = inline_serializer(name="DetailResponse", fields={"detail": s.CharField()})


def _set_auth_cookies(response, user):
    refresh = RefreshToken.for_user(user)

    membership = OrganizationMember.objects.filter(
        user=user, is_active=True
    ).select_related("organization").first()

    refresh["org_id"] = str(membership.organization_id) if membership else None
    refresh["role"] = membership.role if membership else None
    refresh["member_id"] = str(membership.id) if membership else None

    profile = DriverProfile.objects.filter(user=user).first()
    refresh["driver_profile_id"] = str(profile.id) if profile else None

    access = str(refresh.access_token)
    response.set_cookie(
        "access_token", value=access, httponly=True,
        secure=COOKIE_SECURE, samesite="Lax", max_age=ACCESS_TOKEN_MAX_AGE,
    )
    response.set_cookie(
        "refresh_token", value=str(refresh), httponly=True,
        secure=COOKIE_SECURE, samesite="Lax", max_age=REFRESH_TOKEN_MAX_AGE,
    )
    return access


def _clear_auth_cookies(response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")


def _get_session_payload(user):
    membership = OrganizationMember.objects.filter(
        user=user, is_active=True
    ).select_related("organization").first()
    profile = DriverProfile.objects.filter(user=user).first()

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
        "role": membership.role if membership else None,
        "org_id": str(membership.organization_id) if membership else None,
        "org_name": membership.organization.name if membership else None,
        "member_id": str(membership.id) if membership else None,
        "driver_profile_id": str(profile.id) if profile else None,
    }


def _get_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Register organization + first admin",
        description="Creates a new Organization and its first ORG_ADMIN user. Sets httpOnly auth cookies.",
        request=RegisterSerializer,
        responses={201: SessionResponseSerializer, 400: OpenApiResponse(description="Validation error")},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        user = result["user"]
        AuditLog.objects.create(
            organization=result["organization"], actor_user=user,
            action=AuditAction.ORG_CREATED,
            metadata={"org_name": result["organization"].name},
            ip_address=_get_ip(request),
        )
        payload = _get_session_payload(user)
        response = Response(payload, status=status.HTTP_201_CREATED)
        access = _set_auth_cookies(response, user)
        payload["access_token"] = access
        response.data = payload
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Login with email + password",
        description=(
            "Authenticates user and sets httpOnly access_token + refresh_token cookies.\n\n"
            "Response also includes a raw `access_token` field for Swagger/Postman testing."
        ),
        request=LoginSerializer,
        responses={200: SessionResponseSerializer, 400: OpenApiResponse(description="Invalid credentials")},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        payload = _get_session_payload(user)
        response = Response(payload)
        access = _set_auth_cookies(response, user)
        payload["access_token"] = access
        response.data = payload
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"], summary="Refresh access token",
        description="Reads refresh_token from httpOnly cookie and issues a new access_token cookie.",
        request=None,
        responses={200: DetailSerializer, 401: OpenApiResponse(description="No or invalid refresh token")},
    )
    def post(self, request):
        raw_refresh = request.COOKIES.get("refresh_token")
        if not raw_refresh:
            return Response({"detail": "No refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            refresh = RefreshToken(raw_refresh)
            access = str(refresh.access_token)
            response = Response({"detail": "Token refreshed.", "access_token": access})
            response.set_cookie(
                "access_token", value=access, httponly=True,
                secure=COOKIE_SECURE, samesite="Lax", max_age=ACCESS_TOKEN_MAX_AGE,
            )
            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
                refresh.set_jti()
                refresh.set_exp()
                response.set_cookie(
                    "refresh_token", value=str(refresh), httponly=True,
                    secure=COOKIE_SECURE, samesite="Lax", max_age=REFRESH_TOKEN_MAX_AGE,
                )
            return response
        except Exception:
            response = Response(
                {"detail": "Invalid or expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED,
            )
            _clear_auth_cookies(response)
            return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"], summary="Logout", request=None,
        description="Blacklists the refresh token and clears auth cookies.",
        responses={200: DetailSerializer},
    )
    def post(self, request):
        raw_refresh = request.COOKIES.get("refresh_token")
        if raw_refresh:
            try:
                token = RefreshToken(raw_refresh)
                token.blacklist()
            except Exception:
                pass
        response = Response({"detail": "Logged out."})
        _clear_auth_cookies(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"], summary="Get current session",
        description="Returns non-sensitive session metadata for the authenticated user.",
        responses={200: SessionResponseSerializer},
    )
    def get(self, request):
        return Response(_get_session_payload(request.user))
