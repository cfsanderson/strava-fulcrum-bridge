#!/usr/bin/env python3
"""
Sync Strava activities to training calendar database.
This module is called by sync_activities.py after syncing to Fulcrum.
"""

import sqlite3
import os
from datetime import datetime


class ActivitySync:
    def __init__(self, db_path='training_calendar/training_plan.db'):
        self.db_path = db_path

    def sync_activity(self, activity_data):
        """
        Sync a Strava activity to the database and match with planned workout.

        activity_data should contain:
        - id: Strava activity ID
        - start_date_local: ISO format datetime (local time)
        - type: Activity type (Run, Ride, etc.)
        - distance: meters
        - moving_time: seconds
        - average_heartrate: bpm (optional)
        - max_heartrate: bpm (optional)
        - total_elevation_gain: meters (optional)
        """

        if not os.path.exists(self.db_path):
            print(f"✗ Calendar database not found: {self.db_path}")
            print(f"  Run: python3 calendar/import_plan.py <csv_file>")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Parse activity data
        activity_id = str(activity_data['id'])

        # Use start_date_local for accurate date matching
        start_date_str = activity_data.get('start_date_local') or activity_data.get('start_date')
        activity_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).date()
        activity_type = activity_data['type']

        # Convert units
        distance_miles = activity_data.get('distance', 0) / 1609.34  # meters to miles
        duration_minutes = activity_data.get('moving_time', 0) / 60  # seconds to minutes
        elevation_ft = activity_data.get('total_elevation_gain', 0) * 3.28084  # meters to feet

        # Calculate pace (min/mi) for activities with distance
        pace_str = None
        if distance_miles > 0:
            pace_min_per_mile = duration_minutes / distance_miles
            pace_str = f"{int(pace_min_per_mile)}:{int((pace_min_per_mile % 1) * 60):02d} min/mi"

        # Find matching planned workout (same date, compatible type)
        cursor.execute("""
            SELECT id FROM planned_workouts
            WHERE date = ?
            AND (
                workout_type = ?
                OR (workout_type = 'Run' AND ? = 'Run')
                OR (workout_type LIKE 'Burn Bootcamp%' AND ? IN ('WeightTraining', 'Workout', 'Crossfit'))
            )
            LIMIT 1
        """, (str(activity_date), activity_type, activity_type, activity_type))

        match = cursor.fetchone()
        planned_workout_id = match[0] if match else None

        # Insert or update activity
        cursor.execute("""
            INSERT OR REPLACE INTO completed_activities
            (id, planned_workout_id, date, activity_type, distance_miles,
             duration_minutes, avg_pace, avg_hr, max_hr, elevation_gain_ft,
             strava_url, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            activity_id,
            planned_workout_id,
            str(activity_date),
            activity_type,
            distance_miles if distance_miles > 0 else None,
            int(duration_minutes),
            pace_str,
            activity_data.get('average_heartrate'),
            activity_data.get('max_heartrate'),
            int(elevation_ft) if elevation_ft > 0 else None,
            f"https://www.strava.com/activities/{activity_id}",
            datetime.now()
        ))

        conn.commit()
        conn.close()

        if planned_workout_id:
            print(f"✓ Synced activity {activity_id} to calendar (matched: {planned_workout_id})")
        else:
            print(f"✓ Synced activity {activity_id} to calendar (unmatched - extra credit)")

        # Regenerate calendar after syncing
        try:
            from .generator import CalendarGenerator
            generator = CalendarGenerator(self.db_path)
            generator.generate_calendar()
        except Exception as e:
            print(f"✗ Failed to regenerate calendar: {e}")


def sync_from_strava(activity_data):
    """
    Convenience function to sync an activity to the calendar.
    Call this from sync_activities.py after syncing to Fulcrum.

    Example integration in sync_activities.py:

    from calendar.activity_sync import sync_from_strava

    # After syncing to Fulcrum:
    try:
        sync_from_strava(activity)
    except Exception as e:
        print(f"Warning: Calendar sync failed: {e}")
    """

    sync = ActivitySync()
    sync.sync_activity(activity_data)


if __name__ == '__main__':
    # For testing
    print("Testing activity sync with sample data...")

    test_activity = {
        'id': 17017838489,
        'start_date_local': '2026-01-11T16:49:20Z',
        'type': 'Run',
        'distance': 8160.7,  # 5.07 miles
        'moving_time': 3590,  # 59:50
        'average_heartrate': 149,
        'max_heartrate': 164,
        'total_elevation_gain': 148.1  # 486 feet
    }

    sync = ActivitySync()
    sync.sync_activity(test_activity)
