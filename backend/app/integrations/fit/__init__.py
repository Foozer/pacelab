"""Parse Garmin FIT activity files in memory.

FIT import is a user upload, not a live Garmin Connect link. Original bytes
are not persisted. GPS/position fields are dropped.
"""

from app.integrations.fit.parser import (
    FIT_PROVIDER,
    GPS_FIELD_NAMES,
    FitParseError,
    parse_fit_activity,
)

__all__ = ["FIT_PROVIDER", "GPS_FIELD_NAMES", "FitParseError", "parse_fit_activity"]
