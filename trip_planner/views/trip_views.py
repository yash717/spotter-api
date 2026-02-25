from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from trip_planner.constants import AuditAction, MemberRole, TripStatus
from trip_planner.models import AuditLog, CustomUser, Trip
from trip_planner.permissions import CanAccessTrip, IsAnyMember, IsDispatcherOrAbove, get_membership
from trip_planner.serializers import (
    DailyLogSheetSerializer,
    HOSViolationSerializer,
    TripDetailSerializer,
    TripListSerializer,
    TripPlanInputSerializer,
)
from trip_planner.services.trip_simulator import plan_trip

TripAssignRequestSerializer = inline_serializer(
    name="TripAssignRequest", fields={"driver_id": s.UUIDField()}
)
TripStatusRequestSerializer = inline_serializer(
    name="TripStatusRequest", fields={"status": s.ChoiceField(choices=TripStatus.ALL)}
)


class TripPlanView(APIView):
    def get_permissions(self):
        return [IsAnyMember()]

    @extend_schema(
        tags=["Trips"],
        summary="Create trip plan",
        description=(
            "Full planning pipeline: geocode locations → compute route → "
            "HOS simulation → generate stops + daily logs + violations. All persisted atomically."
        ),
        request=TripPlanInputSerializer,
        responses={
            201: TripDetailSerializer,
            400: OpenApiResponse(description="Geocoding or routing error"),
        },
    )
    def post(self, request):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = TripPlanInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        driver = None
        vehicle = None
        profile = getattr(request.user, "driver_profile", None)
        if membership.role == MemberRole.DRIVER and profile:
            driver = request.user
            vehicle = getattr(profile, "assigned_vehicle", None)
        try:
            trip = plan_trip(
                organization=membership.organization,
                created_by=request.user,
                current_location=data["current_location"],
                pickup_location=data["pickup_location"],
                dropoff_location=data["dropoff_location"],
                cycle_used_hours=float(data["cycle_used_hours"]),
                planned_start_datetime=data.get("planned_start_datetime"),
                assigned_driver=driver, vehicle=vehicle,
            )
            AuditLog.objects.create(
                organization=membership.organization, actor_user=request.user,
                action=AuditAction.TRIP_CREATED, metadata={"trip_id": str(trip.id)},
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return Response(TripDetailSerializer(trip).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TripListView(APIView):
    def get_permissions(self):
        return [IsAnyMember()]

    @extend_schema(
        tags=["Trips"],
        summary="List trips",
        description="Drivers see only their assigned trips. Other roles see all org trips.",
        responses={200: TripListSerializer(many=True)},
    )
    def get(self, request):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if membership.role == MemberRole.DRIVER:
            trips = Trip.objects.filter(assigned_driver=request.user)
        else:
            trips = Trip.objects.filter(organization=membership.organization)
        trips = trips.select_related("assigned_driver", "created_by").order_by("-created_at")
        return Response(TripListSerializer(trips, many=True).data)


class TripDetailView(APIView):
    def get_permissions(self):
        return [IsAnyMember(), CanAccessTrip()]

    @extend_schema(
        tags=["Trips"],
        summary="Get trip details",
        description="Full trip with nested stops, daily log sheets (with segments), and HOS violations.",
        responses={200: TripDetailSerializer, 404: OpenApiResponse(description="Not found")},
    )
    def get(self, request, pk):
        try:
            trip = Trip.objects.prefetch_related(
                "stops", "daily_logs__segments", "violations"
            ).select_related("assigned_driver", "created_by", "organization", "vehicle").get(id=pk)
        except Trip.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, trip)
        return Response(TripDetailSerializer(trip).data)


class TripAssignView(APIView):
    def get_permissions(self):
        return [IsDispatcherOrAbove()]

    @extend_schema(
        tags=["Trips"],
        summary="Assign driver to trip",
        request=TripAssignRequestSerializer,
        responses={200: TripDetailSerializer, 404: OpenApiResponse(description="Trip or driver not found")},
    )
    def post(self, request, pk):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            trip = Trip.objects.get(id=pk, organization=membership.organization)
        except Trip.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        driver_id = request.data.get("driver_id")
        if not driver_id:
            return Response({"detail": "driver_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            driver = CustomUser.objects.get(id=driver_id)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Driver not found."}, status=status.HTTP_404_NOT_FOUND)
        trip.assigned_driver = driver
        trip.status = TripStatus.ASSIGNED
        trip.assigned_at = timezone.now()
        trip.save(update_fields=["assigned_driver", "status", "assigned_at"])
        AuditLog.objects.create(
            organization=membership.organization, actor_user=request.user,
            action=AuditAction.TRIP_ASSIGNED,
            metadata={"trip_id": str(trip.id), "driver_email": driver.email},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(TripDetailSerializer(trip).data)


class TripLogsView(APIView):
    def get_permissions(self):
        return [IsAnyMember(), CanAccessTrip()]

    @extend_schema(
        tags=["Trips"],
        summary="Get daily log sheets",
        description="Returns all daily ELD log sheets for a trip, each with duty status segments.",
        responses={200: DailyLogSheetSerializer(many=True)},
    )
    def get(self, request, pk):
        try:
            trip = Trip.objects.prefetch_related("daily_logs__segments").get(id=pk)
        except Trip.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, trip)
        return Response(DailyLogSheetSerializer(trip.daily_logs.all(), many=True).data)


class TripViolationsView(APIView):
    def get_permissions(self):
        return [IsAnyMember(), CanAccessTrip()]

    @extend_schema(
        tags=["Trips"],
        summary="Get HOS violations",
        responses={200: HOSViolationSerializer(many=True)},
    )
    def get(self, request, pk):
        try:
            trip = Trip.objects.prefetch_related("violations").get(id=pk)
        except Trip.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, trip)
        return Response(HOSViolationSerializer(trip.violations.all(), many=True).data)


class TripStatusView(APIView):
    def get_permissions(self):
        return [IsAnyMember()]

    @extend_schema(
        tags=["Trips"],
        summary="Update trip status",
        request=TripStatusRequestSerializer,
        responses={200: TripDetailSerializer, 400: OpenApiResponse(description="Invalid status")},
    )
    def patch(self, request, pk):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            trip = Trip.objects.get(id=pk)
        except Trip.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get("status")
        if new_status not in TripStatus.ALL:
            return Response({"detail": f"Invalid status. Must be one of: {TripStatus.ALL}"}, status=status.HTTP_400_BAD_REQUEST)
        trip.status = new_status
        trip.save(update_fields=["status", "updated_at"])
        return Response(TripDetailSerializer(trip).data)
