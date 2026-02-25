"""
Invitation CRUD views with Swagger docs.
[F5] Rate limited with django-ratelimit.
"""

import jwt
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from trip_planner.models import Invitation
from trip_planner.permissions import IsOrgAdmin, get_membership
from trip_planner.serializers import (
    InvitationAcceptSerializer,
    InvitationCreateSerializer,
    InvitationDetailSerializer,
    InvitationListSerializer,
)
from trip_planner.services.invitation_service import (
    accept_invitation,
    revoke_invitation,
    send_invitation,
    validate_invitation_token,
)
from trip_planner.views.auth_views import _get_ip, _get_session_payload, _set_auth_cookies

ValidateRequestSerializer = inline_serializer(
    name="InvitationValidateRequest", fields={"token": s.CharField()}
)
ValidateResponseSerializer = inline_serializer(
    name="InvitationValidateResponse",
    fields={
        "org_name": s.CharField(),
        "email": s.EmailField(),
        "role": s.CharField(),
        "invitation_id": s.UUIDField(),
    },
)
DetailSerializer = inline_serializer(
    name="InvitationDetailMsg", fields={"detail": s.CharField()}
)


@method_decorator(ratelimit(key="ip", rate="3/m", method="POST", block=True), name="post")
class InvitationListCreateView(APIView):
    def get_permissions(self):
        return [IsOrgAdmin()]

    @extend_schema(
        tags=["Invitations"],
        summary="List org invitations",
        description="Returns all invitations for the authenticated admin's organization.",
        responses={200: InvitationListSerializer(many=True)},
    )
    def get(self, request):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        invitations = Invitation.objects.filter(
            organization=membership.organization
        ).select_related("invited_by")
        return Response(InvitationListSerializer(invitations, many=True).data)

    @extend_schema(
        tags=["Invitations"],
        summary="Send invitation",
        description=(
            "Sends a JWT-signed invitation email. Rate limited: 3/min per IP.\n\n"
            "The invitee receives an email with a link to accept."
        ),
        request=InvitationCreateSerializer,
        responses={
            201: InvitationListSerializer,
            400: OpenApiResponse(description="Validation error"),
            429: OpenApiResponse(description="Rate limit exceeded"),
        },
    )
    def post(self, request):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = InvitationCreateSerializer(
            data=request.data, context={"organization": membership.organization},
        )
        serializer.is_valid(raise_exception=True)
        invitation = send_invitation(
            organization=membership.organization,
            invited_by_user=request.user,
            email=serializer.validated_data["email"],
            role=serializer.validated_data["role"],
            personal_message=serializer.validated_data.get("personal_message", ""),
            ip_address=_get_ip(request),
        )
        return Response(InvitationListSerializer(invitation).data, status=status.HTTP_201_CREATED)


@method_decorator(ratelimit(key="ip", rate="20/h", method="POST", block=True), name="post")
class InvitationValidateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Invitations"],
        summary="Validate invitation token",
        description="Validates a JWT invitation token and returns pre-fill data for the onboarding form.",
        request=ValidateRequestSerializer,
        responses={
            200: ValidateResponseSerializer,
            400: OpenApiResponse(description="Invalid token"),
            409: OpenApiResponse(description="Already accepted"),
            410: OpenApiResponse(description="Expired or revoked"),
        },
    )
    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = validate_invitation_token(token)
            return Response({
                "org_name": payload.get("org_name"),
                "email": payload.get("email"),
                "role": payload.get("role"),
                "invitation_id": payload.get("invitation_id"),
            })
        except jwt.ExpiredSignatureError:
            return Response({"detail": "This invitation has expired."}, status=status.HTTP_410_GONE)
        except jwt.InvalidSignatureError:
            return Response({"detail": "Invalid invitation token."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            msg = str(e)
            if "already been accepted" in msg:
                return Response({"detail": msg}, status=status.HTTP_409_CONFLICT)
            if "revoked" in msg or "expired" in msg:
                return Response({"detail": msg}, status=status.HTTP_410_GONE)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True), name="post")
class InvitationAcceptView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Invitations"],
        summary="Accept invitation + create account",
        description=(
            "Accepts a JWT invitation token, creates the user account + driver profile + vehicle "
            "(if driver role), and sets httpOnly auth cookies. Entire flow is atomic [F6]."
        ),
        request=InvitationAcceptSerializer,
        responses={
            201: OpenApiResponse(description="Account created, cookies set"),
            400: OpenApiResponse(description="Validation error or invalid token"),
            410: OpenApiResponse(description="Token expired"),
        },
    )
    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = accept_invitation(
                token=serializer.validated_data["token"],
                form_data=serializer.validated_data,
                ip_address=_get_ip(request),
            )
            response = Response(_get_session_payload(user), status=status.HTTP_201_CREATED)
            _set_auth_cookies(response, user)
            return response
        except jwt.ExpiredSignatureError:
            return Response({"detail": "This invitation has expired."}, status=status.HTTP_410_GONE)
        except jwt.InvalidSignatureError:
            return Response({"detail": "Invalid invitation token."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InvitationDetailView(APIView):
    def get_permissions(self):
        return [IsOrgAdmin()]

    @extend_schema(
        tags=["Invitations"],
        summary="Get invitation details",
        responses={200: InvitationDetailSerializer, 404: OpenApiResponse(description="Not found")},
    )
    def get(self, request, pk):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            invitation = Invitation.objects.select_related("invited_by", "accepted_by").get(
                id=pk, organization=membership.organization
            )
        except Invitation.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(InvitationDetailSerializer(invitation).data)


class InvitationRevokeView(APIView):
    def get_permissions(self):
        return [IsOrgAdmin()]

    @extend_schema(
        tags=["Invitations"],
        summary="Revoke pending invitation",
        request=None,
        responses={
            200: DetailSerializer,
            400: OpenApiResponse(description="Cannot revoke"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def post(self, request, pk):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            invitation = Invitation.objects.get(id=pk, organization=membership.organization)
        except Invitation.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            revoke_invitation(invitation, request.user, _get_ip(request))
            return Response({"detail": "Invitation revoked."})
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InvitationResendView(APIView):
    def get_permissions(self):
        return [IsOrgAdmin()]

    @extend_schema(
        tags=["Invitations"],
        summary="Resend invitation email",
        request=None,
        responses={
            201: InvitationListSerializer,
            404: OpenApiResponse(description="Pending invitation not found"),
        },
    )
    @method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True))
    def post(self, request, pk):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            invitation = Invitation.objects.get(
                id=pk, organization=membership.organization, status="pending"
            )
        except Invitation.DoesNotExist:
            return Response({"detail": "Pending invitation not found."}, status=status.HTTP_404_NOT_FOUND)
        new_invitation = send_invitation(
            organization=membership.organization,
            invited_by_user=request.user,
            email=invitation.email,
            role=invitation.role,
            personal_message=invitation.personal_message,
            ip_address=_get_ip(request),
        )
        invitation.resend_count += 1
        invitation.save(update_fields=["resend_count"])
        return Response(InvitationListSerializer(new_invitation).data, status=status.HTTP_201_CREATED)
