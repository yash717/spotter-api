import uuid

from django.conf import settings
from django.db import models

from trip_planner.constants import InvitationStatus, MemberRole

from .organization import Organization


class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="invitations"
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invitations",
    )
    email = models.EmailField(db_index=True)
    role = models.CharField(max_length=20, choices=MemberRole.CHOICES)
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=10, choices=InvitationStatus.CHOICES, default=InvitationStatus.PENDING
    )
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_invitations",
    )
    personal_message = models.CharField(max_length=500, blank=True, default="")
    resend_count = models.IntegerField(default=0)
    last_resent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "invitations"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Invite {self.email} as {self.role} ({self.status})"
