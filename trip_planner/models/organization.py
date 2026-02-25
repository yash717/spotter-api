import uuid

from django.conf import settings
from django.db import models

from trip_planner.constants import MemberRole


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    dot_number = models.CharField(max_length=20, blank=True, default="")
    mc_number = models.CharField(max_length=20, blank=True, default="")
    primary_contact_email = models.EmailField(blank=True, default="")
    address = models.CharField(max_length=500, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    logo_url = models.URLField(blank=True, default="")
    invitation_expiry_days = models.IntegerField(default=7)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations"

    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=MemberRole.CHOICES)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="deactivated_members",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invited_members",
    )

    class Meta:
        db_table = "organization_members"
        unique_together = [("organization", "user")]

    def __str__(self):
        return f"{self.user.email} - {self.role} @ {self.organization.name}"
