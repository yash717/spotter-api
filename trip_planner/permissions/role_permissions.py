"""
[F2] Safe permission classes with centralized membership access.
"""

import logging

from rest_framework.permissions import BasePermission

from trip_planner.constants import MemberRole
from trip_planner.models import OrganizationMember

logger = logging.getLogger(__name__)


def get_membership(user):
    if not user or not user.is_authenticated:
        return None
    try:
        return OrganizationMember.objects.select_related("organization").get(
            user=user, is_active=True
        )
    except OrganizationMember.DoesNotExist:
        return None
    except OrganizationMember.MultipleObjectsReturned:
        logger.warning("User %s has multiple active memberships", user.id)
        return None
    except Exception:
        logger.exception("Unexpected error fetching membership for user %s", user.id)
        return None


class IsOrgAdmin(BasePermission):
    def has_permission(self, request, view):
        membership = get_membership(request.user)
        return membership is not None and membership.role == MemberRole.ORG_ADMIN


class IsDispatcherOrAbove(BasePermission):
    ALLOWED_ROLES = {MemberRole.ORG_ADMIN, MemberRole.DISPATCHER}

    def has_permission(self, request, view):
        membership = get_membership(request.user)
        return membership is not None and membership.role in self.ALLOWED_ROLES


class IsFleetManagerOrAbove(BasePermission):
    ALLOWED_ROLES = {MemberRole.ORG_ADMIN, MemberRole.FLEET_MANAGER, MemberRole.DISPATCHER}

    def has_permission(self, request, view):
        membership = get_membership(request.user)
        return membership is not None and membership.role in self.ALLOWED_ROLES


class IsAnyMember(BasePermission):
    def has_permission(self, request, view):
        return get_membership(request.user) is not None


class CanAccessTrip(BasePermission):
    def has_object_permission(self, request, view, obj):
        membership = get_membership(request.user)
        if membership is None:
            return False
        if membership.role in {
            MemberRole.ORG_ADMIN, MemberRole.DISPATCHER,
            MemberRole.VIEWER, MemberRole.FLEET_MANAGER,
        }:
            return str(obj.organization_id) == str(membership.organization_id)
        if membership.role == MemberRole.DRIVER:
            return str(obj.assigned_driver_id) == str(request.user.id)
        return False
