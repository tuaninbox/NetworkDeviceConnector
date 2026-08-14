import aiosmtplib
from email.message import EmailMessage
import logging

from core.settings import settings

logger = logging.getLogger("email")

# Default SMTP config (you can override via config.yaml later)
SMTP_HOST = "smtp.yourdomain.com"
SMTP_PORT = 587
SMTP_USERNAME = "smtp-user"
SMTP_PASSWORD = "smtp-password"
SMTP_FROM = "noreply@yourdomain.com"


async def send_email(to: str, subject: str, body: str):
    """
    Reusable async email sender using SMTP settings from core/settings.py.
    """

    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        # Build SMTP kwargs dynamically
        smtp_kwargs = {
            "hostname": settings.smtp_host,
            "port": settings.smtp_port,
        }

        # Optional authentication
        if settings.smtp_user and settings.smtp_password:
            smtp_kwargs["username"] = settings.smtp_user
            smtp_kwargs["password"] = settings.smtp_password
            smtp_kwargs["start_tls"] = True  # enable TLS only when auth is used

        await aiosmtplib.send(msg, **smtp_kwargs)

        logger.info(f"Email sent to {to}: {subject}")

    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        raise