#!/usr/bin/env python3
"""
Generate iCalendar file from training plan and completed activities.
"""

import sqlite3
import os
from datetime import datetime, date, timedelta
from icalendar import Calendar, Event
import pytz


class CalendarGenerator:
    def __init__(self, db_path='training_calendar/training_plan.db'):
        self.db_path = db_path
        self.timezone = pytz.timezone('America/New_York')

    def generate_calendar(self, output_path='training_calendar/training_calendar.ics'):
        """Generate complete calendar file."""

        if not os.path.exists(self.db_path):
            print(f"✗ Database not found: {self.db_path}")
            print(f"  Run: python3 calendar/import_plan.py <csv_file>")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create calendar
        cal = Calendar()
        cal.add('prodid', '-//Training Calendar//Strava Bridge//EN')
        cal.add('version', '2.0')
        cal.add('x-wr-calname', 'Phase 1 Training - 50K Prep')
        cal.add('x-wr-timezone', 'America/New_York')
        cal.add('x-wr-caldesc', 'Training plan with Strava activity integration')

        # Fetch all planned workouts with completed activity data
        cursor.execute("""
            SELECT
                pw.id,
                pw.date,
                pw.workout_type,
                pw.details,
                pw.duration_minutes,
                pw.distance_miles,
                pw.notes,
                pw.start_time,
                ca.id as activity_id,
                ca.distance_miles as actual_distance,
                ca.duration_minutes as actual_duration,
                ca.avg_pace,
                ca.avg_hr,
                ca.max_hr,
                ca.elevation_gain_ft,
                ca.strava_url,
                ca.start_time as actual_start_time
            FROM planned_workouts pw
            LEFT JOIN completed_activities ca ON pw.id = ca.planned_workout_id
            ORDER BY pw.date
        """)

        planned_count = 0
        completed_count = 0
        today = date.today()

        for row in cursor.fetchall():
            # Skip past incomplete workouts (hide planned workouts that weren't done)
            workout_date = datetime.strptime(row[1], '%Y-%m-%d').date()
            is_completed = row[8] is not None  # activity_id
            is_rest_day = row[2] == 'Rest'

            # Hide past incomplete workouts (except rest days which are always shown)
            if workout_date < today and not is_completed and not is_rest_day:
                continue

            event = self._create_event(row)
            cal.add_component(event)
            planned_count += 1
            if is_completed:
                completed_count += 1

        # Add unmatched activities (extra credit workouts)
        cursor.execute("""
            SELECT
                id,
                date,
                activity_type,
                distance_miles,
                duration_minutes,
                avg_pace,
                avg_hr,
                max_hr,
                elevation_gain_ft,
                strava_url,
                start_time
            FROM completed_activities
            WHERE planned_workout_id IS NULL
            ORDER BY date
        """)

        unmatched_count = 0
        for row in cursor.fetchall():
            event = self._create_unmatched_event(row)
            cal.add_component(event)
            unmatched_count += 1

        conn.close()

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Write to file
        with open(output_path, 'wb') as f:
            f.write(cal.to_ical())

        print(f"✓ Calendar generated: {output_path}")
        print(f"  - {planned_count} planned workouts")
        print(f"  - {completed_count} completed")
        print(f"  - {unmatched_count} unmatched activities (extra credit)")

    def _create_event(self, row):
        """Create iCalendar event from planned workout with optional completed data."""
        (workout_id, date_str, workout_type, details, duration_mins,
         distance_miles, notes, start_time, activity_id, actual_distance,
         actual_duration, avg_pace, avg_hr, max_hr, elevation_gain, strava_url, actual_start_time) = row

        event = Event()

        # Parse date and time
        workout_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Determine if completed
        is_completed = activity_id is not None

        if workout_type == 'Rest':
            # All-day event for rest days
            event.add('summary', '🛌 Rest Day')
            event.add('dtstart', workout_date)
            event.add('dtend', workout_date + timedelta(days=1))
            event['dtstart'].params['VALUE'] = 'DATE'
            event['dtend'].params['VALUE'] = 'DATE'

            desc_parts = []
            if details:
                desc_parts.append(details)
            if notes:
                desc_parts.append(f"\n{notes}")
            event.add('description', '\n'.join(desc_parts))
            event.add('transp', 'TRANSPARENT')

        else:
            # Timed workout event
            # Use actual start time if completed, otherwise use planned start time
            time_to_use = actual_start_time if is_completed and actual_start_time else start_time
            start_hour, start_min, start_sec = map(int, time_to_use.split(':'))
            start_dt = datetime.combine(workout_date, datetime.min.time().replace(hour=start_hour, minute=start_min, second=start_sec))
            start_dt = self.timezone.localize(start_dt)

            # Calculate end time (always use actual duration if completed)
            end_mins = actual_duration if is_completed else (duration_mins or 60)
            end_dt = start_dt + timedelta(minutes=end_mins)

            # Create summary
            if is_completed:
                emoji = '✅'
                dist_str = f" - {actual_distance:.2f}mi" if actual_distance else ""
                summary = f"{emoji} {workout_type}{dist_str}"
            else:
                emoji = '🏃' if workout_type == 'Run' else '💪'
                dist_str = f" - {distance_miles:.1f}mi" if distance_miles else ""
                summary = f"{emoji} {workout_type}{dist_str}"

            event.add('summary', summary)
            event.add('dtstart', start_dt)
            event.add('dtend', end_dt)

            # Create description
            desc_parts = []
            if details:
                desc_parts.append(details)

            if is_completed:
                desc_parts.append(f"\n✅ COMPLETED")
                if avg_pace:
                    desc_parts.append(f"Pace: {avg_pace}")
                if avg_hr:
                    desc_parts.append(f"Avg HR: {avg_hr} (Max: {max_hr})")
                if elevation_gain:
                    desc_parts.append(f"Elevation: {int(elevation_gain)}ft")
                if strava_url:
                    desc_parts.append(f"\nView on Strava: {strava_url}")
            else:
                if duration_mins:
                    desc_parts.append(f"\nPlanned duration: {duration_mins}min")
                if distance_miles:
                    desc_parts.append(f"Planned distance: {distance_miles}mi")

            if notes:
                desc_parts.append(f"\nNotes: {notes}")

            event.add('description', '\n'.join(desc_parts))

        event.add('uid', f"{workout_id}@training-plan")
        event.add('status', 'CONFIRMED')

        return event

    def _create_unmatched_event(self, row):
        """Create event for unmatched activity (extra credit workout)."""
        (activity_id, date_str, activity_type, distance_miles, duration_minutes,
         avg_pace, avg_hr, max_hr, elevation_gain, strava_url, start_time) = row

        event = Event()

        # Parse date
        workout_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Create timed event using actual start time (default to 6:30 AM if not available)
        if start_time:
            start_hour, start_min, start_sec = map(int, start_time.split(':'))
        else:
            start_hour, start_min, start_sec = 6, 30, 0

        start_dt = datetime.combine(workout_date, datetime.min.time().replace(hour=start_hour, minute=start_min, second=start_sec))
        start_dt = self.timezone.localize(start_dt)
        end_dt = start_dt + timedelta(minutes=duration_minutes if duration_minutes else 60)

        # Create summary with "extra credit" indicator
        dist_str = f" - {distance_miles:.2f}mi" if distance_miles else ""
        summary = f"⭐ {activity_type}{dist_str} (Extra)"

        event.add('summary', summary)
        event.add('dtstart', start_dt)
        event.add('dtend', end_dt)

        # Create description
        desc_parts = ["⭐ UNPLANNED ACTIVITY (Extra Credit!)"]

        if avg_pace:
            desc_parts.append(f"Pace: {avg_pace}")
        if avg_hr:
            desc_parts.append(f"Avg HR: {avg_hr} (Max: {max_hr})")
        if elevation_gain:
            desc_parts.append(f"Elevation: {int(elevation_gain)}ft")
        if duration_minutes:
            desc_parts.append(f"Duration: {int(duration_minutes)}min")
        if strava_url:
            desc_parts.append(f"\nView on Strava: {strava_url}")

        event.add('description', '\n'.join(desc_parts))
        event.add('uid', f"strava-{activity_id}@training-plan")
        event.add('status', 'CONFIRMED')

        return event


if __name__ == '__main__':
    generator = CalendarGenerator()
    generator.generate_calendar()
