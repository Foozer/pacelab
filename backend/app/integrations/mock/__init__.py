"""Development and test activity provider (Phase 3).

Supplies realistic running activities so the product can be used without live
Garmin credentials.
"""

from app.integrations.mock.provider import MockActivityProvider

__all__ = ["MockActivityProvider"]
