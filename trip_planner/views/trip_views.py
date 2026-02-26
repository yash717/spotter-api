from django.db.models import Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from trip_planner.constants import AuditAction, MemberRole, TripStatus
from trip_planner.models import AuditLog, Trip, User
from trip_planner.pagination import SpotterPagination
from trip_planner.permissions import CanAccessTrip, IsAnyMember, IsDispatcherOrAbove, get_membership
from trip_planner.schema import paginated_list_schema
from trip_planner.serializers import (
    DailyLogSheetSerializer,
    HOSViolationSerializer,
    TripDetailSerializer,
    TripListSerializer,
    TripPlanInputSerializer,
)
from trip_planner.realtime import broadcast_notification, broadcast_trip_update
from trip_planner.services.email_service import send_trip_assigned_email
from trip_planner.services.trip_simulator import plan_trip

TripAssignRequestSerializer = inline_serializer(
    name="TripAssignRequest", fields={"driver_id": s.UUIDField()}
)
TripStatusRequestSerializer = inline_serializer(
    name="TripStatusRequest", fields={"status": s.ChoiceField(choices=TripStatus.ALL)}
)


@method_decorator(ratelimit(key="user", rate="10/m", method="POST", block=True), name="post")
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
                assigned_driver=driver,
                vehicle=vehicle,
            )
            AuditLog.objects.create(
                organization=membership.organization,
                actor_user=request.user,
                action=AuditAction.TRIP_CREATED,
                metadata={"trip_id": str(trip.id)},
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            broadcast_trip_update(str(trip.id), trip.status)
            broadcast_notification(
                "Trip Created",
                f"New trip {str(trip.id)[:8]} planned",
                variant="success",
                trip_id=str(trip.id),
            )
            return Response(TripDetailSerializer(trip).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TripListView(APIView):
    pagination_class = SpotterPagination

    def get_permissions(self):
        return [IsAnyMember()]

    @extend_schema(
        tags=["Trips"],
        summary="List trips",
        description=(
            "Drivers see only their assigned trips. Other roles see all org trips. "
            "Supports pagination, search (addresses), filter by status, and ordering."
        ),
        parameters=[
            OpenApiParameter("page", int, description="Page number (1-based)"),
            OpenApiParameter("page_size", int, description="Page size (max 100)"),
            OpenApiParameter(
                "search", str, description="Search in current/pickup/dropoff addresses"
            ),
            OpenApiParameter(
                "status", str, description="Filter by trip status", enum=TripStatus.ALL
            ),
            OpenApiParameter(
                "ordering",
                str,
                description="Order by: created_at, -created_at, status, -status, assigned_at, -assigned_at",
                enum=[
                    "created_at",
                    "-created_at",
                    "status",
                    "-status",
                    "assigned_at",
                    "-assigned_at",
                ],
            ),
        ],
        responses={200: paginated_list_schema(TripListSerializer, "TripListPaginated")},
    )
    def get(self, request):
        membership = get_membership(request.user)
        if not membership and not getattr(request.user, "is_superuser", False):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if membership and membership.role == MemberRole.DRIVER:
            trips = Trip.objects.filter(assigned_driver=request.user)
        elif membership:
            trips = Trip.objects.filter(organization=membership.organization)
        else:
            trips = Trip.objects.all()
        trips = trips.select_related("assigned_driver", "created_by", "vehicle")

        search = request.query_params.get("search", "").strip()
        if search:
            q = (
                Q(input_current_address__icontains=search)
                | Q(input_pickup_address__icontains=search)
                | Q(input_dropoff_address__icontains=search)
            )
            trips = trips.filter(q)
        status_filter = request.query_params.get("status", "").strip()
        if status_filter and status_filter in TripStatus.ALL:
            trips = trips.filter(status=status_filter)
        ordering = request.query_params.get("ordering", "-created_at")
        if ordering.lstrip("-") in ("created_at", "status", "assigned_at") and ordering in (
            "created_at",
            "-created_at",
            "status",
            "-status",
            "assigned_at",
            "-assigned_at",
        ):
            trips = trips.order_by(ordering)
        else:
            trips = trips.order_by("-created_at")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(trips, request)
        if page is not None:
            return paginator.get_paginated_response(TripListSerializer(page, many=True).data)
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
            trip = (
                Trip.objects.prefetch_related("stops", "daily_logs__segments", "violations")
                .select_related("assigned_driver", "created_by", "organization", "vehicle")
                .get(id=pk)
            )
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
        responses={
            200: TripDetailSerializer,
            404: OpenApiResponse(description="Trip or driver not found"),
        },
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
            return Response(
                {"detail": "driver_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            driver = User.objects.get(id=driver_id)
        except User.DoesNotExist:
            return Response({"detail": "Driver not found."}, status=status.HTTP_404_NOT_FOUND)
        trip.assigned_driver = driver
        trip.status = TripStatus.ASSIGNED
        trip.assigned_at = timezone.now()
        trip.save(update_fields=["assigned_driver", "status", "assigned_at"])
        AuditLog.objects.create(
            organization=membership.organization,
            actor_user=request.user,
            action=AuditAction.TRIP_ASSIGNED,
            metadata={"trip_id": str(trip.id), "driver_email": driver.email},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        # Send trip assignment email
        driver_profile = getattr(driver, "driver_profile", None)
        driver_name = (
            driver_profile.full_name
            if driver_profile
            else f"{driver.first_name} {driver.last_name}".strip() or driver.email
        )
        vehicle_number = trip.vehicle.truck_number if trip.vehicle else ""
        planned_start = (
            trip.planned_start_datetime.strftime("%Y-%m-%d %H:%M")
            if trip.planned_start_datetime
            else ""
        )

        send_trip_assigned_email(
            driver_email=driver.email,
            driver_name=driver_name,
            trip_id=str(trip.id),
            current_address=trip.input_current_address,
            pickup_address=trip.input_pickup_address,
            dropoff_address=trip.input_dropoff_address,
            total_distance=float(trip.total_trip_distance_miles or 0),
            total_duration=float(trip.total_trip_duration_hours or 0),
            vehicle_number=vehicle_number,
            planned_start_time=planned_start,
        )

        broadcast_trip_update(str(trip.id), TripStatus.ASSIGNED, driver_email=driver.email)
        broadcast_notification(
            "Trip Assigned",
            f"Trip {str(trip.id)[:8]} assigned to {driver.email}",
            variant="success",
            trip_id=str(trip.id),
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
            return Response(
                {"detail": f"Invalid status. Must be one of: {TripStatus.ALL}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        trip.status = new_status
        trip.save(update_fields=["status", "updated_at"])

        broadcast_trip_update(str(trip.id), new_status)
        broadcast_notification(
            "Trip Status Updated",
            f"Trip {str(trip.id)[:8]} → {new_status}",
            variant="info",
            trip_id=str(trip.id),
        )

        return Response(TripDetailSerializer(trip).data)
