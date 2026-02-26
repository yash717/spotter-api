import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _get_common_context():
    """Get common context variables for all email templates."""
    return {
        "current_year": datetime.now().year,
        "support_url": f"{settings.FRONTEND_URL}/support",
        "privacy_url": f"{settings.FRONTEND_URL}/privacy",
        "terms_url": f"{settings.FRONTEND_URL}/terms",
    }


def send_invitation_email(
    to_email: str,
    org_name: str,
    role: str,
    invite_url: str,
    personal_message: str = "",
    invited_by_name: str = "",
    expires_in_days: int = 7,
) -> bool:
    """Send invitation email using the branded HTML template."""
    subject = "You're Invited to Join Spotter AI"
    expires_in = f"{expires_in_days} day{'s' if expires_in_days != 1 else ''}"

    context = {
        **_get_common_context(),
        "invited_by_name": invited_by_name or "Your administrator",
        "app_name": org_name,
        "invitation_url": invite_url,
        "expires_in": expires_in,
        "email": to_email,
    }
    html_message = render_to_string("trip_planner/emails/invitation.html", context)

    plain_text = (
        f"{invited_by_name or 'Your administrator'} has invited you to join {org_name} on Spotter AI.\n\n"
        f"Accept your invitation: {invite_url}\n\n"
        f"This invitation expires in {expires_in}.\n\n"
        "— Spotter AI Team"
    )

    try:
        send_mail(
            subject=subject,
            message=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Invitation email sent to %s for org %s", to_email, org_name)
        return True
    except Exception:
        logger.exception("Failed to send invitation email to %s", to_email)
        return False


def send_welcome_email(user_email: str, user_name: str, org_name: str, user_role: str) -> bool:
    """Send welcome email to a new user."""
    subject = f"Welcome to {org_name} - Spotter AI"
    login_url = f"{settings.FRONTEND_URL}/login"

    context = {
        **_get_common_context(),
        "user_name": user_name,
        "user_email": user_email,
        "org_name": org_name,
        "user_role": user_role,
        "login_url": login_url,
    }
    html_message = render_to_string("trip_planner/emails/welcome.html", context)

    plain_text = (
        f"Hi {user_name},\n\n"
        f"Welcome to {org_name} on Spotter AI! Your account has been successfully created.\n\n"
        f"Login: {login_url}\n\n"
        f"Your Role: {user_role}\n\n"
        "— Spotter AI Team"
    )

    try:
        send_mail(
            subject=subject,
            message=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Welcome email sent to %s", user_email)
        return True
    except Exception:
        logger.exception("Failed to send welcome email to %s", user_email)
        return False


def send_trip_assigned_email(
    driver_email: str,
    driver_name: str,
    trip_id: str,
    current_address: str,
    pickup_address: str,
    dropoff_address: str,
    total_distance: float,
    total_duration: float,
    vehicle_number: str = "",
    planned_start_time: str = "",
) -> bool:
    """Send trip assignment notification email."""
    subject = f"New Trip Assigned - {trip_id}"
    trip_url = f"{settings.FRONTEND_URL}/trips/{trip_id}"

    context = {
        **_get_common_context(),
        "driver_name": driver_name,
        "trip_id": trip_id,
        "current_address": current_address,
        "pickup_address": pickup_address,
        "dropoff_address": dropoff_address,
        "total_distance": f"{total_distance:.1f}",
        "total_duration": f"{total_duration:.1f}",
        "vehicle_number": vehicle_number,
        "planned_start_time": planned_start_time,
        "trip_url": trip_url,
    }
    html_message = render_to_string("trip_planner/emails/trip_assigned.html", context)

    plain_text = (
        f"Hi {driver_name},\n\n"
        f"You have been assigned a new trip.\n\n"
        f"From: {current_address}\n"
        f"Pickup: {pickup_address}\n"
        f"Dropoff: {dropoff_address}\n"
        f"Distance: {total_distance:.1f} miles\n"
        f"Duration: {total_duration:.1f} hours\n\n"
        f"View details: {trip_url}\n\n"
        "— Spotter AI Team"
    )

    try:
        send_mail(
            subject=subject,
            message=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[driver_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Trip assigned email sent to %s for trip %s", driver_email, trip_id)
        return True
    except Exception:
        logger.exception("Failed to send trip assigned email to %s", driver_email)
        return False


def send_violation_alert_email(
    driver_email: str,
    driver_name: str,
    trip_id: str,
    violation_type: str,
    violation_severity: str,
    description: str,
    violation_time: str = "",
) -> bool:
    """Send HOS violation alert email."""
    subject = f"HOS Violation Alert - {violation_type}"
    trip_url = f"{settings.FRONTEND_URL}/trips/{trip_id}"

    context = {
        **_get_common_context(),
        "driver_name": driver_name,
        "trip_id": trip_id,
        "violation_type": violation_type,
        "violation_severity": violation_severity,
        "description": description,
        "violation_time": violation_time,
        "trip_url": trip_url,
    }
    html_message = render_to_string("trip_planner/emails/violation_alert.html", context)

    plain_text = (
        f"Hi {driver_name},\n\n"
        f"A {violation_severity} HOS violation has been detected.\n\n"
        f"Type: {violation_type}\n"
        f"Description: {description}\n"
        f"Trip: {trip_id}\n\n"
        f"View details: {trip_url}\n\n"
        "— Spotter AI Team"
    )

    try:
        send_mail(
            subject=subject,
            message=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[driver_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Violation alert email sent to %s for trip %s", driver_email, trip_id)
        return True
    except Exception:
        logger.exception("Failed to send violation alert email to %s", driver_email)
        return False
