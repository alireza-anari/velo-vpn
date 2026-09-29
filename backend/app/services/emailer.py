from __future__ import annotations

import smtplib
from email.message import EmailMessage
from ..config import settings


def send_email(to: str, subject: str, body: str) -> bool:
    if not (settings.smtp_host and settings.smtp_from and to):
        return False
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
            client.starttls()
            if settings.smtp_user:
                client.login(settings.smtp_user, settings.smtp_password)
            client.send_message(msg)
        return True
    except OSError:
        return False
