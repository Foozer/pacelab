"""Select the configured activity provider.

Default is mock. Garmin is a stub until official OAuth credentials exist.
"""

from app.core.config import Settings
from app.integrations.garmin import GarminActivityProvider
from app.integrations.mock import MockActivityProvider
from app.integrations.protocol import ActivityProvider


def build_activity_provider(settings: Settings) -> ActivityProvider:
    if settings.activity_provider == "garmin":
        return GarminActivityProvider()
    return MockActivityProvider()
