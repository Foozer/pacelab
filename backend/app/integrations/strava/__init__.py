"""Official Strava OAuth package.

Uses https://www.strava.com/oauth/* and https://www.strava.com/api/v3/*.
Does not scrape Strava or store usernames/passwords.
"""

from app.integrations.strava.provider import StravaActivityProvider

__all__ = ["StravaActivityProvider"]
