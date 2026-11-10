import asyncio
import logging
import smtplib
from email.message import EmailMessage
from config.settings import settings

logger = logging.getLogger("taskmate.email")


def _send_sync(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM or settings.SMTP_USER or "no-reply@taskmate.local"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    if settings.SMTP_PORT == 465:  # SSL mula umpisa
        smtp = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
    else:
        smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
    with smtp:
        if settings.SMTP_PORT != 465:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
        smtp.send_message(message)


async def send_email(to: str, subject: str, body: str) -> None:
    """Hindi nagra-raise: ginagamit ito sa background task, at hindi dapat malaman ng user kung may email."""
    if not settings.SMTP_HOST:
        # dev lang: walang SMTP, kaya makikita ang laman sa log
        logger.warning("SMTP is not configured. Email to %s | %s\n%s", to, subject, body)
        return
    try:
        await asyncio.to_thread(_send_sync, to, subject, body)  # sync ang smtplib
    except Exception:
        logger.exception("Failed to send email to %s", to)


async def send_password_reset_email(to: str, code: str) -> None:
    await send_email(
        to,
        "TaskMate password reset code",
        f"Your TaskMate password reset code is {code}.\n\n"
        "It expires in 10 minutes. If you did not ask for this, you can ignore this email.",
    )
