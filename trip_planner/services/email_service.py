import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_invitation_email(
    to_email: str,
    org_name: str,
    role: str,
    invite_url: str,
    personal_message: str = "",
    invited_by_name: str = "",
    expires_in_days: int = 7,
) -> bool:
    """
    Sends invitation email via configured backend
    (SendGrid in production, console in development).
    """
    subject = f"You're invited to join {org_name} on Spotter ELD"

    role_display = role.replace("_", " ").title()

    plain_text = (
        f"You've been invited to join {org_name} as a {role_display}.\n\n"
    )
    if personal_message:
        plain_text += f'Message from {invited_by_name}: "{personal_message}"\n\n'
    plain_text += (
        f"Click the link below to accept your invitation:\n{invite_url}\n\n"
        f"This invitation expires in {expires_in_days} days.\n\n"
        "— Spotter ELD Team"
    )

    html_message = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;
                background: #141414; color: #FFFFFF; padding: 40px; border-radius: 12px;">
        <h1 style="color: #FFFFFF; margin-bottom: 8px;">Spotter ELD</h1>
        <hr style="border-color: #2E2E2E; margin: 20px 0;" />
        <h2 style="color: #FFFFFF;">You're invited to join {org_name}</h2>
        <p style="color: #A3A3A3;">
            as a <strong style="color: #FFFFFF;">{role_display}</strong>
        </p>
    """
    if personal_message:
        html_message += f"""
        <div style="background: #1C1C1C; padding: 16px; border-radius: 8px;
                    margin: 20px 0; border-left: 3px solid #276EF1;">
            <p style="color: #A3A3A3; margin: 0 0 4px 0; font-size: 13px;">
                Message from {invited_by_name}:
            </p>
            <p style="color: #FFFFFF; margin: 0;">"{personal_message}"</p>
        </div>
        """
    html_message += f"""
        <a href="{invite_url}"
           style="display: inline-block; background: #276EF1; color: #FFFFFF;
                  padding: 14px 32px; border-radius: 8px; text-decoration: none;
                  font-weight: 600; margin: 20px 0;">
            Accept Invitation
        </a>
        <p style="color: #525252; font-size: 13px; margin-top: 30px;">
            This invitation expires in {expires_in_days} days.
        </p>
        <hr style="border-color: #2E2E2E; margin: 20px 0;" />
        <p style="color: #525252; font-size: 12px;">Spotter ELD — HOS-Compliant Route Planning</p>
    </div>
    """

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
