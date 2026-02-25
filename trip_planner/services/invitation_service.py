"""
Invitation JWT engine.
[F1] Uses INVITATION_JWT_SECRET (separate from Django SECRET_KEY).
[F6] accept_invitation() runs inside @transaction.atomic().
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.db import transaction
from django.utils import timezone as dj_tz

from trip_planner.constants import AuditAction, InvitationStatus, MemberRole
from trip_planner.models import (
    AuditLog,
    CustomUser,
    DriverProfile,
    Invitation,
    OrganizationMember,
    Vehicle,
)

logger = logging.getLogger(__name__)

INVITE_SECRET = None
INVITE_ALG = None


def _get_secret():
    global INVITE_SECRET, INVITE_ALG
    if INVITE_SECRET is None:
        INVITE_SECRET = settings.INVITATION_JWT_SECRET
        INVITE_ALG = getattr(settings, "INVITATION_JWT_ALGORITHM", "HS256")
    return INVITE_SECRET, INVITE_ALG


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_invitation_token(invitation):
    secret, alg = _get_secret()
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "spotter-eld",
        "sub": "invitation",
        "invitation_id": str(invitation.id),
        "org_id": str(invitation.organization_id),
        "org_name": invitation.organization.name,
        "email": invitation.email,
        "role": invitation.role,
        "invited_by": str(invitation.invited_by_id),
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(days=invitation.organization.invitation_expiry_days)).timestamp()
        ),
    }
    return jwt.encode(payload, secret, algorithm=alg)


def validate_invitation_token(token: str) -> dict:
    secret, alg = _get_secret()
    payload = jwt.decode(token, secret, algorithms=[alg])

    invitation_id = payload.get("invitation_id")
    try:
        invitation = Invitation.objects.select_related("organization").get(id=invitation_id)
    except Invitation.DoesNotExist:
        raise ValueError("Invitation not found.")

    if invitation.status == InvitationStatus.ACCEPTED:
        raise ValueError("This invitation has already been accepted.")
    if invitation.status == InvitationStatus.REVOKED:
        raise ValueError("This invitation has been revoked.")
    if invitation.status == InvitationStatus.EXPIRED:
        raise ValueError("This invitation has expired.")

    return payload


def send_invitation(organization, invited_by_user, email, role, personal_message="", ip_address=None):
    from .email_service import send_invitation_email

    Invitation.objects.filter(
        organization=organization, email=email, status=InvitationStatus.PENDING
    ).update(status=InvitationStatus.REVOKED)

    invitation = Invitation(
        organization=organization,
        invited_by=invited_by_user,
        email=email,
        role=role,
        personal_message=personal_message,
        token_hash="placeholder",
        expires_at=dj_tz.now() + timedelta(days=organization.invitation_expiry_days),
    )
    invitation.save()

    token = generate_invitation_token(invitation)
    invitation.token_hash = hash_token(token)
    invitation.save(update_fields=["token_hash"])

    invite_url = f"{settings.FRONTEND_URL}/accept-invite?token={token}"
    send_invitation_email(
        to_email=email, org_name=organization.name, role=role,
        invite_url=invite_url, personal_message=personal_message,
        invited_by_name=f"{invited_by_user.first_name} {invited_by_user.last_name}".strip(),
        expires_in_days=organization.invitation_expiry_days,
    )

    AuditLog.objects.create(
        organization=organization, actor_user=invited_by_user,
        action=AuditAction.INVITATION_SENT,
        metadata={"invitee_email": email, "role": role, "invitation_id": str(invitation.id)},
        ip_address=ip_address,
    )
    return invitation


@transaction.atomic
def accept_invitation(token: str, form_data: dict, ip_address=None):
    secret, alg = _get_secret()
    payload = jwt.decode(token, secret, algorithms=[alg])

    invitation = Invitation.objects.select_for_update().get(id=payload["invitation_id"])

    if invitation.status != InvitationStatus.PENDING:
        raise ValueError(f"Invitation is no longer pending (status: {invitation.status}).")

    email = payload["email"]
    role = payload["role"]
    org_id = payload["org_id"]
    full_name = form_data.get("full_name", "")

    user, user_created = CustomUser.objects.get_or_create(
        email=email,
        defaults={
            "username": email,
            "first_name": full_name.split(" ")[0] if full_name else "",
            "last_name": " ".join(full_name.split(" ")[1:]) if full_name else "",
        },
    )
    if user_created:
        user.set_password(form_data.get("password", ""))
        user.save()

    profile, _ = DriverProfile.objects.get_or_create(
        user=user,
        defaults={
            "full_name": full_name,
            "license_number": form_data.get("license_number", ""),
            "license_state": form_data.get("license_state", ""),
            "home_terminal_address": form_data.get("home_terminal_address", ""),
            "current_cycle_used_hours": form_data.get("cycle_used_hours", 0),
            "profile_completed_at": dj_tz.now(),
        },
    )

    if role == MemberRole.DRIVER and form_data.get("truck_number"):
        truck_number = form_data["truck_number"]
        existing = Vehicle.objects.select_for_update().filter(
            organization_id=org_id, truck_number=truck_number
        ).first()

        if existing and existing.assigned_driver_profile is not None:
            raise ValueError(
                f"Truck {truck_number} is already assigned to another driver. "
                "Ask your admin to unassign it first."
            )
        elif existing:
            existing.assigned_driver_profile = profile
            existing.trailer_number = form_data.get("trailer_number", existing.trailer_number)
            existing.odometer_current = form_data.get("odometer", existing.odometer_current)
            existing.save()
        else:
            Vehicle.objects.create(
                organization_id=org_id, assigned_driver_profile=profile,
                truck_number=truck_number,
                trailer_number=form_data.get("trailer_number", ""),
                license_plate=form_data.get("license_plate", ""),
                odometer_current=form_data.get("odometer", 0),
            )

    member = OrganizationMember.objects.create(
        organization_id=org_id, user=user, role=role,
        invited_by=invitation.invited_by,
    )
    profile.org_member = member
    profile.save(update_fields=["org_member"])

    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = dj_tz.now()
    invitation.accepted_by = user
    invitation.save(update_fields=["status", "accepted_at", "accepted_by"])

    AuditLog.objects.create(
        organization_id=org_id, actor_user=user,
        action=AuditAction.INVITATION_ACCEPTED,
        metadata={"email": email, "role": role, "invitation_id": str(invitation.id)},
        ip_address=ip_address,
    )
    return user


def revoke_invitation(invitation, revoked_by_user, ip_address=None):
    if invitation.status != InvitationStatus.PENDING:
        raise ValueError(f"Cannot revoke invitation with status '{invitation.status}'.")

    invitation.status = InvitationStatus.REVOKED
    invitation.save(update_fields=["status"])

    AuditLog.objects.create(
        organization=invitation.organization, actor_user=revoked_by_user,
        action=AuditAction.INVITATION_REVOKED,
        metadata={"invitee_email": invitation.email, "invitation_id": str(invitation.id)},
        ip_address=ip_address,
    )
