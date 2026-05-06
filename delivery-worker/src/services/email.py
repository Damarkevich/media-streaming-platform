import logging

import brevo
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)

from src.core.config import settings

logger = logging.getLogger(__name__)

_client: brevo.AsyncBrevo | None = None


def get_brevo_client() -> brevo.AsyncBrevo:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = brevo.AsyncBrevo(api_key=settings.brevo_api_key)
    return _client


async def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
) -> bool:
    """Send a transactional email via Brevo. Returns True on success."""
    try:
        await get_brevo_client().transactional_emails.send_transac_email(
            to=[SendTransacEmailRequestToItem(email=to_email, name=to_name)],
            sender=SendTransacEmailRequestSender(
                name=settings.brevo_sender_name,
                email=settings.brevo_sender_email,
            ),
            subject=subject,
            html_content=html_content,
        )
    except Exception:
        logger.exception("Brevo send_transac_email failed for %s", to_email)
        return False
    else:
        logger.info("Email sent to %s", to_email)
        return True
