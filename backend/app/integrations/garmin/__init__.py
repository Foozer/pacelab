"""Official Garmin Connect Developer Program integration (deferred).

This package must not invent API endpoints or store unofficial credentials.
Live OAuth waits until the official programme accepts new apps. Garmin-recorded
runs enter PaceLab today by uploading .fit files (Phase 7), not this stub.
"""

from app.integrations.garmin.provider import GarminActivityProvider

__all__ = ["GarminActivityProvider"]
