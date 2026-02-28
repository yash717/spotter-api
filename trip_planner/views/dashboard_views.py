from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import timedelta

from trip_planner.constants import TripStatus
from trip_planner.models import Trip, DailyLogSheet, HOSViolation, DutyStatusSegment
from trip_planner.permissions import IsAnyMember
from trip_planner.serializers import (
    DashboardStatsSerializer,
    DashboardTripSummarySerializer,
    DriverDashboardSerializer,
)


@method_decorator(ratelimit(key="user", rate="30/m", method="GET", block=True), name="get")
class DriverDashboardStatsView(APIView):
    """
    API endpoint to retrieve driver dashboard statistics.
    
    Returns:
    - Cycle hours used/remaining
    - Weekly trip count
    - Total miles driven
    - Active violations
    - On-duty and driving hours
    """

    def get_permissions(self):
        return [IsAnyMember()]

    @extend_schema(
        tags=["Dashboard"],
        summary="Get driver dashboard stats",
        description="Retrieve aggregated statistics for driver dashboard including cycle hours, trips, and violations.",
        responses=DashboardStatsSerializer,
    )
    def get(self, request):
        user = request.user
        now = timezone.now()
        cycle_start = now - timedelta(days=7)  # Assuming 7-day rolling cycle
        week_start = now - timedelta(days=7)

        # Get all trips for the user
        all_trips = Trip.objects.filter(assigned_driver=user)
        
        # Get trips in current cycle
        cycle_trips = all_trips.filter(
            created_at__gte=cycle_start
        )

        # Get trips from this week
        weekly_trips = all_trips.filter(
            created_at__gte=week_start
        )

        # Calculate cycle hours used
        cycle_used_hours = (
            DailyLogSheet.objects.filter(trip__in=cycle_trips).aggregate(
                total=Sum("total_driving_hours_day")
            )["total"]
            or 0
        )
        
        # Get on-duty hours
        on_duty_hours = (
            DailyLogSheet.objects.filter(trip__in=cycle_trips).aggregate(
                total=Sum("total_on_duty_nd_hours_day")
            )["total"]
            or 0
        )
        
        # Get driving hours
        driving_hours = (
            DailyLogSheet.objects.filter(trip__in=cycle_trips).aggregate(
                total=Sum("total_driving_hours_day")
            )["total"]
            or 0
        )

        cycle_remaining_hours = max(0, 70 - float(cycle_used_hours))
        cycle_percentage = min(100, int((float(cycle_used_hours) / 70) * 100))

        # Get total miles
        total_miles = (
            cycle_trips.aggregate(total=Sum("total_trip_distance_miles"))[
                "total"
            ]
            or 0
        )

        # Get active violations
        active_violations = HOSViolation.objects.filter(
            trip__in=cycle_trips, resolved_at__isnull=True
        ).count()

        stats = {
            "cycle_used_hours": cycle_used_hours,
            "cycle_remaining_hours": cycle_remaining_hours,
            "cycle_percentage": cycle_percentage,
            "weekly_trip_count": weekly_trips.count(),
            "total_miles_driven": total_miles,
            "active_violations": active_violations,
            "on_duty_hours": on_duty_hours,
            "driving_hours": driving_hours,
        }

        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data, status=status.HTTP_200_OK)


@method_decorator(ratelimit(key="user", rate="30/m", method="GET", block=True), name="get")
class DriverUpcomingTripsView(APIView):
    """
    API endpoint to retrieve upcoming trips for a driver.
    
    Returns:
    - Current active trip
    - Next 5 upcoming trips
    """

    def get_permissions(self):
        return [IsAnyMember()]

    @extend_schema(
        tags=["Dashboard"],
        summary="Get driver upcoming trips",
        description="Retrieve current and upcoming trips assigned to the driver.",
    )
    def get(self, request):
        user = request.user
        now = timezone.now()

        # Get current trip (ASSIGNED or ACTIVE status)
        current_trip = (
            Trip.objects.filter(
                assigned_driver=user,
                status__in=[TripStatus.ASSIGNED, TripStatus.ACTIVE],
            )
            .order_by("-assigned_at")
            .first()
        )

        # Get upcoming trips (ASSIGNED status)
        upcoming_trips = Trip.objects.filter(
            assigned_driver=user, status=TripStatus.ASSIGNED
        ).order_by("planned_start_datetime")[:5]

        data = {
            "current_trip": current_trip,
            "upcoming_trips": upcoming_trips,
        }

        return Response(
            {
                "current_trip": DashboardTripSummarySerializer(current_trip).data
                if current_trip
                else None,
                "upcoming_trips": DashboardTripSummarySerializer(
                    upcoming_trips, many=True
                ).data,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(ratelimit(key="user", rate="20/m", method="GET", block=True), name="get")
class DriverDashboardView(APIView):
    """
    Comprehensive driver dashboard endpoint.
    
    Returns combined stats and trip information for a single request.
    """

    def get_permissions(self):
        return [IsAnyMember()]

    @extend_schema(
        tags=["Dashboard"],
        summary="Get complete driver dashboard",
        description="Retrieve all dashboard data including stats and upcoming trips in a single request.",
        responses=DriverDashboardSerializer,
    )
    def get(self, request):
        user = request.user
        now = timezone.now()
        cycle_start = now - timedelta(days=7)
        week_start = now - timedelta(days=7)

        # Get all trips
        all_trips = Trip.objects.filter(assigned_driver=user)
        cycle_trips = all_trips.filter(created_at__gte=cycle_start)
        weekly_trips = all_trips.filter(created_at__gte=week_start)

        # Calculate stats
        cycle_used_hours = (
            DailyLogSheet.objects.filter(trip__in=cycle_trips).aggregate(
                total=Sum("total_driving_hours_day")
            )["total"]
            or 0
        )
        
        on_duty_hours = (
            DailyLogSheet.objects.filter(trip__in=cycle_trips).aggregate(
                total=Sum("total_on_duty_nd_hours_day")
            )["total"]
            or 0
        )
        
        driving_hours = (
            DailyLogSheet.objects.filter(trip__in=cycle_trips).aggregate(
                total=Sum("total_driving_hours_day")
            )["total"]
            or 0
        )

        cycle_remaining_hours = max(0, 70 - float(cycle_used_hours))
        cycle_percentage = min(100, int((float(cycle_used_hours) / 70) * 100))

        total_miles = (
            cycle_trips.aggregate(total=Sum("total_trip_distance_miles"))[
                "total"
            ]
            or 0
        )

        active_violations = HOSViolation.objects.filter(
            trip__in=cycle_trips, resolved_at__isnull=True
        ).count()

        stats = {
            "cycle_used_hours": cycle_used_hours,
            "cycle_remaining_hours": cycle_remaining_hours,
            "cycle_percentage": cycle_percentage,
            "weekly_trip_count": weekly_trips.count(),
            "total_miles_driven": total_miles,
            "active_violations": active_violations,
            "on_duty_hours": on_duty_hours,
            "driving_hours": driving_hours,
        }

        # Get trips
        current_trip = (
            Trip.objects.filter(
                assigned_driver=user,
                status__in=[TripStatus.ASSIGNED, TripStatus.ACTIVE],
            )
            .order_by("-assigned_at")
            .first()
        )

        upcoming_trips = Trip.objects.filter(
            assigned_driver=user, status=TripStatus.ASSIGNED
        ).order_by("planned_start_datetime")[:5]

        data = {
            "stats": stats,
            "current_trip": current_trip,
            "upcoming_trips": upcoming_trips,
        }

        serializer = DriverDashboardSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
