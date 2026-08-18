"""Authentication request and response schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class CsrfResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    csrf_token: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class EmailVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=16, max_length=256)


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=16, max_length=256)
    password: str = Field(min_length=10, max_length=128)


class DevOutboxItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template: str
    subject: str
    body: str


class DevOutboxResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emails: list[DevOutboxItem]
