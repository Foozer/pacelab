"""Outbound email abstraction.

Sender selection happens in `create_app` via `create_email_sender`:

- SMTP env set → `SmtpEmailSender` (production, or local if you configure SMTP)
- otherwise, non-production → `RecordingEmailSender` (tests and local Account-page outbox)
- production with empty SMTP → fail fast in `Settings.validate_for_environment`

Never log recipients in full, verification/reset tokens, or message bodies.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutboundEmail:
    to: str
    subject: str
    body: str
    template: str
    token: str


class EmailSender(Protocol):
    async def send(self, email: OutboundEmail) -> None: ...


class SmtpTransport(Protocol):
    """Synchronous SMTP (or test double). Never used against a real host in CI."""

    def send(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        message: EmailMessage,
    ) -> None: ...


class StdlibSmtpTransport:
    """STARTTLS on typical submission ports; implicit TLS on 465 (Resend/SES/Postmark)."""

    def send(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        message: EmailMessage,
    ) -> None:
        client: smtplib.SMTP
        if port == 465:
            client = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            client = smtplib.SMTP(host, port, timeout=30)
            client.ehlo()
            client.starttls()
            client.ehlo()
        try:
            if username:
                client.login(username, password)
            client.send_message(message)
        finally:
            client.quit()


@dataclass
class RecordingEmailSender:
    """Stores outbound mail in memory. Never log the token or full body."""

    outbox: list[OutboundEmail] = field(default_factory=list)

    async def send(self, email: OutboundEmail) -> None:
        self.outbox.append(email)
        logger.info("Queued %s email (recipient and token not logged)", email.template)


class SmtpEmailSender:
    """Sends through SMTP. Tokens stay in the message body only, never in logs."""

    def __init__(
        self,
        settings: Settings,
        transport: SmtpTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport or StdlibSmtpTransport()

    async def send(self, email: OutboundEmail) -> None:
        message = EmailMessage()
        message["From"] = self._settings.smtp_from
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.body)
        try:
            await asyncio.to_thread(
                self._transport.send,
                host=self._settings.smtp_host,
                port=self._settings.smtp_port,
                username=self._settings.smtp_username,
                password=self._settings.smtp_password,
                message=message,
            )
        except Exception:
            logger.exception(
                "Failed to send %s email (recipient and token not logged)",
                email.template,
            )
            raise
        logger.info("Sent %s email (recipient and token not logged)", email.template)


def create_email_sender(
    settings: Settings,
    *,
    transport: SmtpTransport | None = None,
) -> EmailSender:
    """Pick SMTP when configured; otherwise the in-memory recorder (never in production)."""
    if settings.smtp_configured:
        return SmtpEmailSender(settings, transport=transport)
    return RecordingEmailSender()


def verification_email(to: str, frontend_url: str, token: str) -> OutboundEmail:
    verify_url = f"{frontend_url.rstrip('/')}/verify-email?token={token}"
    body = (
        "PaceLab email verification\n\n"
        "Confirm this email address by opening:\n"
        f"{verify_url}\n\n"
        "This link expires in 24 hours. If you did not create a PaceLab account, "
        "you can ignore this message.\n"
    )
    return OutboundEmail(
        to=to,
        subject="Confirm your PaceLab email",
        body=body,
        template="email_verification",
        token=token,
    )


def password_reset_email(to: str, frontend_url: str, token: str) -> OutboundEmail:
    reset_url = f"{frontend_url.rstrip('/')}/reset-password?token={token}"
    body = (
        "PaceLab password reset\n\n"
        "Reset your password by opening:\n"
        f"{reset_url}\n\n"
        "This link expires in 1 hour. If you did not request a reset, you can "
        "ignore this message.\n"
    )
    return OutboundEmail(
        to=to,
        subject="Reset your PaceLab password",
        body=body,
        template="password_reset",
        token=token,
    )
