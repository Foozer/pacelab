"""External activity data providers.

Garmin Connect access must use the official Garmin Connect Developer Program
and OAuth 2.0. Do not scrape Garmin Connect or collect Garmin passwords.

Provider implementations (ActivityProvider protocol, MockActivityProvider,
GarminActivityProvider) are added in later phases. This package exists so those
implementations have a stable import path.
"""
