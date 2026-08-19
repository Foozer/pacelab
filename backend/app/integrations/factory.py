"""Select the configured activity provider for POST /api/v1/activities/sync.

Default is mock. Garmin is a stub until official OAuth credentials exist.
Strava is a per-user connection (POST /api/v1/strava/sync), not ACTIVITY_PROVIDER.
FIT import is a push path (upload), not a pull provider.
"""

from app.core.config import Settings
from app.integrations.garmin import GarminActivityProvider
from app.integrations.mock import MockActivityProvider
from app.integrations.protocol import ActivityProvider


def build_activity_provider(settings: Settings) -> ActivityProvider:
    if settings.activity_provider == "garmin":
        return GarminActivityProvider()
    return MockActivityProvider()
