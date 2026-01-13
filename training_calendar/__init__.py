"""
Training calendar integration for strava-fulcrum-bridge.

This package provides:
- SQLite database for storing planned workouts and completed activities
- iCalendar generation combining planned and actual data
- HTTP server for calendar subscription
- Automatic sync from Strava activities

Usage:
    # Import training plan
    python3 calendar/import_plan.py phase1_training_plan.csv

    # Generate calendar
    python3 calendar/generator.py

    # Start calendar server
    python3 calendar/server.py

    # Sync activity (called from sync_activities.py)
    from calendar.activity_sync import sync_from_strava
    sync_from_strava(activity_data)
"""

from .generator import CalendarGenerator
from .activity_sync import ActivitySync, sync_from_strava

__all__ = ['CalendarGenerator', 'ActivitySync', 'sync_from_strava']
__version__ = '1.0.0'
