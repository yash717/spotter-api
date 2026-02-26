from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from trip_planner.permissions import IsAnyMember, get_membership
from trip_planner.services.geocoding import geocode_autocomplete


@method_decorator(ratelimit(key="user", rate="60/m", method="GET", block=True), name="get")
class GeocodeAutocompleteView(APIView):
    def get_permissions(self):
        return [IsAnyMember()]

    @extend_schema(
        tags=["Geocoding"],
        summary="Address autocomplete",
        description="Returns address suggestions for autocomplete. Uses OpenRouteService when configured.",
        parameters=[
            OpenApiParameter("q", str, description="Search query (address or city)"),
            OpenApiParameter("limit", int, description="Max results (default 5)", required=False),
        ],
        responses={200: {"type": "array", "items": {"type": "object", "properties": {"label": {"type": "string"}, "lat": {"type": "number"}, "lng": {"type": "number"}}}}},
    )
    def get(self, request):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        q = (request.query_params.get("q") or "").strip()
        limit = min(int(request.query_params.get("limit") or 5), 10)
        if not q:
            return Response([])
        suggestions = geocode_autocomplete(q, limit=limit)
        return Response(suggestions)
