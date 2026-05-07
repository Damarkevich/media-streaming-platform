"""Unified notification sending service.

Consolidates email sending logic from delivery and review_liked consumers.
Handles user fetch, template rendering, email delivery, and idempotency recording.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from . import auth_client, email, idempotency, template_renderer

logger = logging.getLogger(__name__)


async def send_notification(
    session: AsyncSession | None = None,
    *,
    user_id: str,
    template: dict,
    variables: dict,
    idempotency_key: str,
) -> bool:
    """Send notification email and record delivery.

    Performs all steps: fetch user, build to_name, render, send, record.
    Returns True if email was sent successfully, False otherwise.

    Args:
        session: SQLAlchemy session for recording delivery. If None, creates own.
        user_id: Target user ID.
        template: Dict with 'subject_template' and 'body_template' keys.
        variables: Template variables (first_name, last_name, etc.).
        idempotency_key: Idempotency key for recording.

    Returns:
        True if email sent (status=SENT), False if error (status=FAILED).
    """
    # Fetch user email
    user = await auth_client.get_user(user_id)
    if user is None:
        logger.warning("User %s not found, cannot send notification", user_id)
        # Try to record FAILED status, but continue if it fails
        try:
            await idempotency.finalize_key(
                idempotency_key=idempotency_key,
                status="FAILED",
                error="User not found",
                session=session,
            )
        except Exception:
            logger.exception("Failed to finalize key after user not found")
        return False

    to_email: str = user["email"]
    first_name: str = user.get("first_name") or ""
    last_name: str = user.get("last_name") or ""
    to_name = f"{first_name} {last_name}".strip() or to_email

    # Render template
    render_variables = {
        "first_name": first_name,
        "last_name": last_name,
        **variables,
    }
    try:
        subject, body = template_renderer.render(
            template["subject_template"],
            template["body_template"],
            render_variables,
        )
    except Exception:
        logger.exception("Template render failed")
        try:
            await idempotency.finalize_key(
                idempotency_key=idempotency_key,
                status="FAILED",
                error="Template render failed",
                session=session,
            )
        except Exception:
            logger.exception("Failed to finalize key after render error")
        return False

    # Send email
    sent_at: datetime | None = None
    error: str | None = None
    status = "FAILED"
    ok = await email.send_email(to_email, to_name, subject, body)
    if ok:
        status = "SENT"
        sent_at = datetime.now(UTC)
    else:
        error = "Brevo send_transac_email returned error"

    # Record delivery
    try:
        await idempotency.finalize_key(
            idempotency_key=idempotency_key,
            status=status,
            sent_at=sent_at,
            error=error,
            session=session,
        )
    except Exception:
        logger.exception("Failed to finalize key")
        return False

    return status == "SENT"
