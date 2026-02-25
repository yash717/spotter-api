from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from trip_planner.models import DriverProfile
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
            return Response({"detail": "Driver profile not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DriverProfileSerializer(profile).data)

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
            return Response({"detail": "Driver profile not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DriverProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DriverProfileSerializer(profile).data)
