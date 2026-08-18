"""SQLAlchemy declarative base. Models in later phases register against this metadata."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all PaceLab ORM models."""
