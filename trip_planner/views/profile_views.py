from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from trip_planner.constants import AuditAction
from trip_planner.models import AuditLog, DriverProfile
from trip_planner.permissions import get_membership
from trip_planner.serializers import DriverProfileSerializer


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Profile"],
        summary="Get driver profile",
        responses={
            200: DriverProfileSerializer,
            404: OpenApiResponse(description="Profile not found"),
        },
    )
    def get(self, request):
        try:
            profile = DriverProfile.objects.select_related("user").get(user=request.user)
        except DriverProfile.DoesNotExist:
            return Response(
                {"detail": "Driver profile not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(DriverProfileSerializer(profile).data)

    @extend_schema(
        tags=["Profile"],
        summary="Create driver profile",
        description="Create a new driver profile. Available when user has no profile yet.",
        request=DriverProfileSerializer,
        responses={
            201: DriverProfileSerializer,
            400: OpenApiResponse(description="Profile already exists or invalid"),
        },
    )
    def post(self, request):
        if DriverProfile.objects.filter(user=request.user).exists():
            return Response(
                {"detail": "Driver profile already exists. Use PUT to update."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership = get_membership(request.user)
        if not membership:
            return Response(
                {"detail": "You must belong to an organization to create a driver profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = dict(request.data)
        if not data.get("full_name"):
            data["full_name"] = (
                f"{request.user.first_name or ''} {request.user.last_name or ''}".strip()
                or request.user.email
            )
        serializer = DriverProfileSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = DriverProfile.objects.create(
            user=request.user,
            org_member=membership,
            full_name=serializer.validated_data["full_name"],
            license_number=serializer.validated_data.get("license_number", ""),
            license_state=(serializer.validated_data.get("license_state") or "")[:5],
            home_terminal_address=serializer.validated_data.get("home_terminal_address", ""),
            co_driver_name=serializer.validated_data.get("co_driver_name", ""),
            current_cycle_used_hours=float(serializer.validated_data.get("current_cycle_used_hours") or 0),
        )
        AuditLog.objects.create(
            organization=membership.organization,
            actor_user=request.user,
            action=AuditAction.PROFILE_CREATED,
            metadata={"driver_profile_id": str(profile.id), "full_name": profile.full_name},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(DriverProfileSerializer(profile).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Profile"],
        summary="Update driver profile",
        description="Partial update of driver profile fields.",
        request=DriverProfileSerializer,
        responses={200: DriverProfileSerializer},
    )
    def put(self, request):
        try:
            profile = DriverProfile.objects.select_related("user").get(user=request.user)
        except DriverProfile.DoesNotExist:
            return Response(
                {"detail": "Driver profile not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = DriverProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        membership = get_membership(request.user)
        if membership:
            AuditLog.objects.create(
                organization=membership.organization,
                actor_user=request.user,
                action=AuditAction.PROFILE_UPDATED,
                metadata={"driver_profile_id": str(profile.id), "full_name": profile.full_name},
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        return Response(DriverProfileSerializer(profile).data)
