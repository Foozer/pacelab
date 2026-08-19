"""Official Strava OAuth integration (Phase 8, not started).

This package must not call strava.com or store unofficial credentials.
"""

from app.integrations.strava.provider import StravaActivityProvider

__all__ = ["StravaActivityProvider"]
