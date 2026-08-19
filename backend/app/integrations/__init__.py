"""Activity ingestion providers.

Ingestion:
- mock — development/seed
- fit — user-uploaded FIT files (Phase 7); not an ActivityProvider pull
- strava — official Strava OAuth (Phase 8, stub only)
- garmin — official Connect Developer Program OAuth (deferred; stub only)

This package must not scrape Garmin or Strava, invent API URLs, or store
Garmin/Strava usernames or passwords.
"""
