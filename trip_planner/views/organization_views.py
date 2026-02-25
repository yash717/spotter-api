from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from trip_planner.constants import AuditAction
from trip_planner.models import AuditLog, OrganizationMember
from trip_planner.permissions import IsAnyMember, IsOrgAdmin, get_membership
from trip_planner.serializers import (
    MemberSerializer,
    MemberUpdateSerializer,
    OrganizationSerializer,
)

DetailSerializer = inline_serializer(name="OrgDetailMsg", fields={"detail": s.CharField()})


class OrganizationDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [IsOrgAdmin()]
        return [IsAnyMember()]

    @extend_schema(
        tags=["Organization"],
        summary="Get organization details",
        responses={200: OrganizationSerializer},
    )
    def get(self, request):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(OrganizationSerializer(membership.organization).data)

    @extend_schema(
        tags=["Organization"],
        summary="Update organization settings",
        description="Partial update. Only org_admin can modify.",
        request=OrganizationSerializer,
        responses={200: OrganizationSerializer},
    )
    def put(self, request):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = OrganizationSerializer(membership.organization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MemberListView(APIView):
    def get_permissions(self):
        return [IsOrgAdmin()]

    @extend_schema(
        tags=["Organization"],
        summary="List org members",
        responses={200: MemberSerializer(many=True)},
    )
    def get(self, request):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        members = OrganizationMember.objects.filter(
            organization=membership.organization
        ).select_related("user").order_by("-joined_at")
        return Response(MemberSerializer(members, many=True).data)


class MemberDetailView(APIView):
    def get_permissions(self):
        return [IsOrgAdmin()]

    @extend_schema(
        tags=["Organization"],
        summary="Get member details",
        responses={200: MemberSerializer, 404: OpenApiResponse(description="Not found")},
    )
    def get(self, request, pk):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            member = OrganizationMember.objects.select_related("user").get(
                id=pk, organization=membership.organization
            )
        except OrganizationMember.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(MemberSerializer(member).data)

    @extend_schema(
        tags=["Organization"],
        summary="Update member role",
        request=MemberUpdateSerializer,
        responses={200: MemberSerializer, 400: OpenApiResponse(description="Cannot change own role")},
    )
    def patch(self, request, pk):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            member = OrganizationMember.objects.get(id=pk, organization=membership.organization)
        except OrganizationMember.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if str(member.user_id) == str(request.user.id):
            return Response({"detail": "You cannot change your own role."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = MemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member.role = serializer.validated_data["role"]
        member.save(update_fields=["role"])
        return Response(MemberSerializer(member).data)

    @extend_schema(
        tags=["Organization"],
        summary="Deactivate member",
        description="Soft-deletes the member (sets is_active=False). Cannot deactivate yourself.",
        request=None,
        responses={200: DetailSerializer, 400: OpenApiResponse(description="Cannot self-deactivate")},
    )
    def delete(self, request, pk):
        membership = get_membership(request.user)
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            member = OrganizationMember.objects.get(
                id=pk, organization=membership.organization, is_active=True
            )
        except OrganizationMember.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if str(member.user_id) == str(request.user.id):
            return Response({"detail": "You cannot deactivate yourself."}, status=status.HTTP_400_BAD_REQUEST)
        member.is_active = False
        member.deactivated_at = timezone.now()
        member.deactivated_by = request.user
        member.save(update_fields=["is_active", "deactivated_at", "deactivated_by"])
        AuditLog.objects.create(
            organization=membership.organization, actor_user=request.user,
            action=AuditAction.MEMBER_DEACTIVATED,
            metadata={"member_email": member.user.email, "member_role": member.role},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response({"detail": "Member deactivated."})
