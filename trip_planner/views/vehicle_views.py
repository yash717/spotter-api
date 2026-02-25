from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from trip_planner.constants import AuditAction
from trip_planner.models import AuditLog, DriverProfile, Vehicle
from trip_planner.permissions import IsAnyMember, IsFleetManagerOrAbove, get_membership
from trip_planner.serializers import VehicleAssignSerializer, VehicleCreateSerializer, VehicleSerializer

DetailSerializer = inline_serializer(name="VehicleDetailMsg", fields={"detail": s.CharField()})


class VehicleListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsFleetManagerOrAbove()]
        return [IsAnyMember()]

    @extend_schema(
        tags=["Vehicles"],
        summary="List org vehicles",
        responses={200: VehicleSerializer(many=True)},
    )
    def get(self, request):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        vehicles = Vehicle.objects.filter(
            organization=membership.organization
        ).select_related("assigned_driver_profile")
        return Response(VehicleSerializer(vehicles, many=True).data)

    @extend_schema(
        tags=["Vehicles"],
        summary="Add vehicle to fleet",
        request=VehicleCreateSerializer,
        responses={201: VehicleSerializer, 400: OpenApiResponse(description="Validation error")},
    )
    def post(self, request):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = VehicleCreateSerializer(
            data=request.data, context={"organization": membership.organization},
        )
        serializer.is_valid(raise_exception=True)
        vehicle = serializer.save(organization=membership.organization)
        return Response(VehicleSerializer(vehicle).data, status=status.HTTP_201_CREATED)


class VehicleDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsFleetManagerOrAbove()]
        return [IsAnyMember()]

    def _get_vehicle(self, request, pk):
        membership = get_membership(request.user)
        if not membership:
            return None, None
        try:
            vehicle = Vehicle.objects.select_related("assigned_driver_profile").get(
                id=pk, organization=membership.organization
            )
            return vehicle, membership
        except Vehicle.DoesNotExist:
            return None, membership

    @extend_schema(
        tags=["Vehicles"],
        summary="Get vehicle details",
        responses={200: VehicleSerializer, 404: OpenApiResponse(description="Not found")},
    )
    def get(self, request, pk):
        vehicle, membership = self._get_vehicle(request, pk)
        if membership is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if vehicle is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(VehicleSerializer(vehicle).data)

    @extend_schema(
        tags=["Vehicles"],
        summary="Update vehicle",
        request=VehicleCreateSerializer,
        responses={200: VehicleSerializer},
    )
    def put(self, request, pk):
        vehicle, membership = self._get_vehicle(request, pk)
        if membership is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if vehicle is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = VehicleCreateSerializer(vehicle, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(VehicleSerializer(vehicle).data)

    @extend_schema(
        tags=["Vehicles"],
        summary="Deactivate vehicle",
        request=None,
        responses={200: DetailSerializer},
    )
    def delete(self, request, pk):
        vehicle, membership = self._get_vehicle(request, pk)
        if membership is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if vehicle is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        vehicle.is_active = False
        vehicle.save(update_fields=["is_active"])
        return Response({"detail": "Vehicle deactivated."})


class VehicleAssignView(APIView):
    def get_permissions(self):
        return [IsFleetManagerOrAbove()]

    @extend_schema(
        tags=["Vehicles"],
        summary="Assign vehicle to driver",
        request=VehicleAssignSerializer,
        responses={
            200: VehicleSerializer,
            404: OpenApiResponse(description="Vehicle or driver not found"),
            409: OpenApiResponse(description="Vehicle already assigned"),
        },
    )
    def post(self, request, pk):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            vehicle = Vehicle.objects.get(id=pk, organization=membership.organization)
        except Vehicle.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = VehicleAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            profile = DriverProfile.objects.get(id=serializer.validated_data["driver_profile_id"])
        except DriverProfile.DoesNotExist:
            return Response({"detail": "Driver profile not found."}, status=status.HTTP_404_NOT_FOUND)
        if vehicle.assigned_driver_profile and vehicle.assigned_driver_profile != profile:
            return Response({"detail": "Vehicle is already assigned. Unassign first."}, status=status.HTTP_409_CONFLICT)
        vehicle.assigned_driver_profile = profile
        vehicle.save(update_fields=["assigned_driver_profile"])
        AuditLog.objects.create(
            organization=membership.organization, actor_user=request.user,
            action=AuditAction.VEHICLE_ASSIGNED,
            metadata={"vehicle_id": str(vehicle.id), "truck_number": vehicle.truck_number, "driver_profile_id": str(profile.id)},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(VehicleSerializer(vehicle).data)


class VehicleUnassignView(APIView):
    def get_permissions(self):
        return [IsFleetManagerOrAbove()]

    @extend_schema(
        tags=["Vehicles"],
        summary="Unassign vehicle from driver",
        request=None,
        responses={200: VehicleSerializer},
    )
    def post(self, request, pk):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            vehicle = Vehicle.objects.get(id=pk, organization=membership.organization)
        except Vehicle.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        vehicle.assigned_driver_profile = None
        vehicle.save(update_fields=["assigned_driver_profile"])
        AuditLog.objects.create(
            organization=membership.organization, actor_user=request.user,
            action=AuditAction.VEHICLE_UNASSIGNED,
            metadata={"vehicle_id": str(vehicle.id), "truck_number": vehicle.truck_number},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(VehicleSerializer(vehicle).data)
