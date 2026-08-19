"""SMTP sender and production mail-config tests. No real SMTP or mail APIs."""

from __future__ import annotations

from email.message import EmailMessage
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.main import create_app
from app.services import email as email_module
from app.services.email import (
    RecordingEmailSender,
    SmtpEmailSender,
    create_email_sender,
    verification_email,
)

PRODUCTION_SECRET = "this-is-a-long-enough-production-secret-key"
DATABASE_URL = "postgresql+asyncpg://pacelab:pacelab@localhost:5432/pacelab"


class RecordingSmtpTransport:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        message: EmailMessage,
    ) -> None:
        self.messages.append(message)


def _development_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "secret_key": "a-sufficiently-long-secret",
        "database_url": DATABASE_URL,
        "environment": "development",
        "debug": False,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def _production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "secret_key": PRODUCTION_SECRET,
        "database_url": DATABASE_URL,
        "environment": "production",
        "debug": False,
        "frontend_url": "https://pacelab.example",
        "allowed_hosts": "pacelab.example",
        "smtp_host": "smtp.resend.com",
        "smtp_port": 465,
        "smtp_username": "resend",
        "smtp_password": "re_test_placeholder",
        "smtp_from": "PaceLab <noreply@pacelab.example>",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_production_rejects_empty_smtp() -> None:
    settings = _production_settings(smtp_host="", smtp_from="", smtp_username="", smtp_password="")
    with pytest.raises(ValueError, match="SMTP_HOST"):
        settings.validate_for_environment()


def test_production_rejects_http_frontend_url() -> None:
    settings = _production_settings(frontend_url="http://pacelab.example")
    with pytest.raises(ValueError, match="https"):
        settings.validate_for_environment()


def test_production_create_app_refuses_empty_smtp() -> None:
    settings = _production_settings(smtp_host="", smtp_from="")
    with pytest.raises(ValueError, match="SMTP"):
        create_app(settings)


def test_production_create_app_uses_smtp_sender() -> None:
    settings = _production_settings()
    settings.validate_for_environment()
    app = create_app(settings)
    assert isinstance(app.state.email_sender, SmtpEmailSender)


def test_development_create_app_uses_recording_sender_without_smtp() -> None:
    settings = _development_settings()
    app = create_app(settings)
    assert isinstance(app.state.email_sender, RecordingEmailSender)


def test_create_email_sender_picks_smtp_when_configured() -> None:
    settings = _development_settings(
        smtp_host="smtp.example.test",
        smtp_from="noreply@example.test",
    )
    sender = create_email_sender(settings, transport=RecordingSmtpTransport())
    assert isinstance(sender, SmtpEmailSender)


@pytest.mark.asyncio
async def test_smtp_verification_includes_https_url_and_does_not_log_token() -> None:
    token = "super-secret-verify-token-value"
    transport = RecordingSmtpTransport()
    settings = _production_settings()
    sender = SmtpEmailSender(settings, transport=transport)
    outbound = verification_email("friend@example.com", settings.frontend_url, token)

    with patch.object(email_module.logger, "info") as mocked_info:
        await sender.send(outbound)

    assert len(transport.messages) == 1
    payload = transport.messages[0].as_string()
    assert "https://pacelab.example/verify-email?token=" in payload
    assert token in payload
    assert "Confirm your PaceLab email" in transport.messages[0]["Subject"]

    assert mocked_info.called
    rendered: list[str] = []
    for call in mocked_info.call_args_list:
        args = call.args
        if args and "%" in str(args[0]) and len(args) > 1:
            rendered.append(str(args[0]) % args[1:])
        else:
            rendered.append(" ".join(str(part) for part in args))
        rendered.append(str(call.kwargs))
    logged = " ".join(rendered)
    assert token not in logged
    assert "friend@example.com" not in logged
    assert "Queued" not in logged
    assert "email_verification" in logged
    assert "recipient and token not logged" in logged
