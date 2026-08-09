import smtplib
from email.message import EmailMessage
from core.settings import settings

def send_email(to: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
        if settings.smtp_user and settings.smtp_password:
            s.starttls()
            s.login(settings.smtp_user, settings.smtp_password)
        s.send_message(msg)
