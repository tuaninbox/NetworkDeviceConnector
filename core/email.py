import aiosmtplib
from email.message import EmailMessage
import logging
import asyncio

from core.settings import settings
from core.audit_logger import log_action


logger = logging.getLogger("email")


def normalize_user(user):
    """
    Normalizes user input for logging:
    - Account model → use username + role
    - str → username only
    - None → anonymous
    """
    if hasattr(user, "username"):
        return user.username, getattr(user, "role", None)
    elif isinstance(user, str):
        return user, None
    else:
        return "anonymous", None


async def send_email(to: str, subject: str, body: str, request=None, user=None):
    """
    Reusable async email sender using SMTP settings from core/settings.py.
    Includes audit logging via log_action().
    """

    username, role = normalize_user(user)

    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        smtp_kwargs = {
            "hostname": settings.smtp_host,
            "port": settings.smtp_port,
        }

        # Optional authentication
        if settings.smtp_user and settings.smtp_password:
            smtp_kwargs["username"] = settings.smtp_user
            smtp_kwargs["password"] = settings.smtp_password
            smtp_kwargs["start_tls"] = True

        await aiosmtplib.send(msg, **smtp_kwargs)

        # Audit log
        if request:
            log_action(
                user,
                "email_sent",
                f"Email sent to {to} with subject '{subject}'",
                request,
                category="email",
            )

        logger.info(f"Email sent to {to}: {subject}")

    except Exception as e:
        if request:
            log_action(
                user,
                "email_failed",
                f"Failed to send email to {to}: {e}",
                request,
                category="email",
                status="error",
            )

        # Optional but useful for debugging
        logger.error(f"Failed to send email to {to}: {e}")

        raise


async def main():
    """
    Run this file directly to send a test email:
    python core/email.py
    """
    to = input("Send test email to: ").strip()
    subject = "Breakglass Test Email"
    body = "This is a test email from Breakglass."

    print(f"Sending email to {to}...")
    await send_email(to, subject, body)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
