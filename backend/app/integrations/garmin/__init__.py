"""Official Garmin Connect Developer Program integration (Phase 7).

This package must not invent API endpoints or store unofficial credentials.
The live provider is implemented only after Garmin developer access is granted.
Until then, the application uses mock and seed data. FIT-file import is not implemented.
"""

from app.integrations.garmin.provider import GarminActivityProvider

__all__ = ["GarminActivityProvider"]
