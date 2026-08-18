"""Outbound email abstraction.

No SMTP provider is configured in Phase 2. A recording sender captures messages
for tests and local development so verification and password-reset flows can be
exercised without logging tokens.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

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


@dataclass
class RecordingEmailSender:
    """Stores outbound mail in memory. Never log the token or full body."""

    outbox: list[OutboundEmail] = field(default_factory=list)

    async def send(self, email: OutboundEmail) -> None:
        self.outbox.append(email)
        logger.info("Queued %s email (recipient and token not logged)", email.template)


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
