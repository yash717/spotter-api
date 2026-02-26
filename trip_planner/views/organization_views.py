from django.db.models import Q
from django.utils import timezone
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

from trip_planner.constants import AuditAction, MemberRole
from trip_planner.models import AuditLog, DriverProfile, OrganizationMember
from trip_planner.pagination import SpotterPagination
from trip_planner.permissions import IsAnyMember, IsOrgAdmin, get_membership
from trip_planner.schema import paginated_list_schema
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
            if getattr(request.user, "is_superuser", False):
                return Response(
                    {"detail": "Platform admin has no organization."},
                    status=status.HTTP_404_NOT_FOUND,
                )
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
            if getattr(request.user, "is_superuser", False):
                return Response(
                    {"detail": "Platform admin has no organization to update."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = OrganizationSerializer(
            membership.organization, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MemberListView(APIView):
    pagination_class = SpotterPagination

    def get_permissions(self):
        return [IsAnyMember()]

    @extend_schema(
        tags=["Organization"],
        summary="List org members",
        description="Paginated list with optional search (email, first_name, last_name) and ordering.",
        parameters=[
            OpenApiParameter("page", int, description="Page number (1-based)"),
            OpenApiParameter("page_size", int, description="Page size (max 100)"),
            OpenApiParameter(
                "search", str, description="Search in user email, first_name, last_name"
            ),
            OpenApiParameter(
                "role",
                str,
                description="Filter by member role (e.g. DRIVER)",
            ),
            OpenApiParameter(
                "ordering",
                str,
                description="Order by: joined_at, -joined_at, role, -role",
                enum=["joined_at", "-joined_at", "role", "-role"],
            ),
        ],
        responses={200: paginated_list_schema(MemberSerializer, "MemberListPaginated")},
    )
    def get(self, request):
        membership = get_membership(request.user)
        if not membership and not getattr(request.user, "is_superuser", False):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if membership:
            members = OrganizationMember.objects.filter(
                organization=membership.organization
            ).select_related("user")
        else:
            members = OrganizationMember.objects.filter(is_active=True).select_related(
                "user", "organization"
            )

        role_filter = request.query_params.get("role", "").strip().upper()
        if role_filter and role_filter in MemberRole.ALL:
            members = members.filter(role=role_filter)

        search = request.query_params.get("search", "").strip()
        if search:
            q = (
                Q(user__email__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
            )
            members = members.filter(q)
        ordering = request.query_params.get("ordering", "-joined_at")
        if ordering.lstrip("-") in ("joined_at", "role") and ordering in (
            "joined_at",
            "-joined_at",
            "role",
            "-role",
        ):
            members = members.order_by(ordering)
        else:
            members = members.order_by("-joined_at")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(members, request)
        if page is not None:
            return paginator.get_paginated_response(MemberSerializer(page, many=True).data)
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
        if not membership and not getattr(request.user, "is_superuser", False):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            if getattr(request.user, "is_superuser", False):
                member = OrganizationMember.objects.select_related(
                    "user", "organization"
                ).get(id=pk)
            else:
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
        responses={
            200: MemberSerializer,
            400: OpenApiResponse(description="Cannot change own role"),
        },
    )
    def patch(self, request, pk):
        membership = get_membership(request.user)
        if not membership and not getattr(request.user, "is_superuser", False):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            if getattr(request.user, "is_superuser", False):
                member = OrganizationMember.objects.get(id=pk)
            else:
                member = OrganizationMember.objects.get(
                    id=pk, organization=membership.organization
                )
        except OrganizationMember.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if str(member.user_id) == str(request.user.id):
            return Response(
                {"detail": "You cannot change your own role."}, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = MemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data["role"]
        member.role = new_role
        member.save(update_fields=["role"])
        if new_role == MemberRole.DRIVER and not DriverProfile.objects.filter(user=member.user).exists():
            full_name = (
                f"{member.user.first_name or ''} {member.user.last_name or ''}".strip()
                or member.user.email
            )
            DriverProfile.objects.create(
                user=member.user,
                org_member=member,
                full_name=full_name,
            )
        return Response(MemberSerializer(member).data)

    @extend_schema(
        tags=["Organization"],
        summary="Deactivate member",
        description="Soft-deletes the member (sets is_active=False). Cannot deactivate yourself.",
        request=None,
        responses={
            200: DetailSerializer,
            400: OpenApiResponse(description="Cannot self-deactivate"),
        },
    )
    def delete(self, request, pk):
        membership = get_membership(request.user)
        if not membership and not getattr(request.user, "is_superuser", False):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            if getattr(request.user, "is_superuser", False):
                member = OrganizationMember.objects.select_related(
                    "organization"
                ).get(id=pk, is_active=True)
            else:
                member = OrganizationMember.objects.get(
                    id=pk, organization=membership.organization, is_active=True
                )
        except OrganizationMember.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if str(member.user_id) == str(request.user.id):
            return Response(
                {"detail": "You cannot deactivate yourself."}, status=status.HTTP_400_BAD_REQUEST
            )
        org = member.organization
        member.is_active = False
        member.deactivated_at = timezone.now()
        member.deactivated_by = request.user
        member.save(update_fields=["is_active", "deactivated_at", "deactivated_by"])
        AuditLog.objects.create(
            organization=org,
            actor_user=request.user,
            action=AuditAction.MEMBER_DEACTIVATED,
            metadata={"member_email": member.user.email, "member_role": member.role},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response({"detail": "Member deactivated."})
