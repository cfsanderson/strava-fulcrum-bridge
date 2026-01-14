#!/usr/bin/env python3
"""
Edit training calendar metadata and regenerate the .ics file.

Usage:
    ./edit_calendar.py update-note 2026-01-13 "Felt great today!"
    ./edit_calendar.py update-title 2026-01-13 "Easy Recovery Run"
    ./edit_calendar.py list 7  # Show next 7 days
"""

import sys
import sqlite3
import argparse
from datetime import datetime, timedelta
from training_calendar.generator import CalendarGenerator


class CalendarEditor:
    def __init__(self, db_path='training_calendar/training_plan.db'):
        self.db_path = db_path
        self.generator = CalendarGenerator(db_path)

    def update_note(self, date_str, note_text):
        """Update notes field for a planned workout."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if workout exists
        cursor.execute("SELECT id, workout_type, notes FROM planned_workouts WHERE date = ?", (date_str,))
        result = cursor.fetchone()

        if not result:
            print(f"✗ No planned workout found for {date_str}")
            conn.close()
            return False

        workout_id, workout_type, old_notes = result
        print(f"Found: {workout_type} on {date_str}")
        if old_notes:
            print(f"Old notes: {old_notes}")

        # Update notes
        cursor.execute("UPDATE planned_workouts SET notes = ? WHERE date = ?", (note_text, date_str))
        conn.commit()
        conn.close()

        print(f"✓ Updated notes: {note_text}")
        return True

    def update_title(self, date_str, title_text):
        """Update details/title field for a planned workout."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if workout exists
        cursor.execute("SELECT id, workout_type, details FROM planned_workouts WHERE date = ?", (date_str,))
        result = cursor.fetchone()

        if not result:
            print(f"✗ No planned workout found for {date_str}")
            conn.close()
            return False

        workout_id, workout_type, old_details = result
        print(f"Found: {workout_type} on {date_str}")
        if old_details:
            print(f"Old title: {old_details}")

        # Update details
        cursor.execute("UPDATE planned_workouts SET details = ? WHERE date = ?", (title_text, date_str))
        conn.commit()
        conn.close()

        print(f"✓ Updated title: {title_text}")
        return True

    def list_workouts(self, days=7, start_date=None):
        """List upcoming workouts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if start_date is None:
            start_date = datetime.now().date().isoformat()

        end_date = (datetime.strptime(start_date, '%Y-%m-%d').date() + timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                pw.date,
                pw.workout_type,
                pw.details,
                pw.distance_miles,
                pw.notes,
                ca.id as completed
            FROM planned_workouts pw
            LEFT JOIN completed_activities ca ON pw.id = ca.planned_workout_id
            WHERE pw.date >= ? AND pw.date < ?
            ORDER BY pw.date
        """, (start_date, end_date))

        print(f"\n📅 Workouts from {start_date} to {end_date}:\n")
        for row in cursor.fetchall():
            date, workout_type, details, distance, notes, completed = row
            status = "✅" if completed else "  "
            dist_str = f" ({distance:.1f}mi)" if distance else ""
            print(f"{status} {date} - {workout_type}{dist_str}")
            if details:
                print(f"         {details}")
            if notes:
                print(f"         📝 {notes}")
            print()

        conn.close()

    def regenerate(self):
        """Regenerate the calendar file."""
        print("\n🔄 Regenerating calendar...")
        self.generator.generate_calendar()


def main():
    parser = argparse.ArgumentParser(
        description='Edit training calendar metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s update-note 2026-01-13 "Felt great today!"
  %(prog)s update-title 2026-01-13 "Easy Recovery Run"
  %(prog)s list 7
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # update-note command
    note_parser = subparsers.add_parser('update-note', help='Update notes for a workout')
    note_parser.add_argument('date', help='Date in YYYY-MM-DD format')
    note_parser.add_argument('note', help='Note text')
    note_parser.add_argument('--no-regen', action='store_true', help='Skip calendar regeneration')

    # update-title command
    title_parser = subparsers.add_parser('update-title', help='Update title/details for a workout')
    title_parser.add_argument('date', help='Date in YYYY-MM-DD format')
    title_parser.add_argument('title', help='Title text')
    title_parser.add_argument('--no-regen', action='store_true', help='Skip calendar regeneration')

    # list command
    list_parser = subparsers.add_parser('list', help='List upcoming workouts')
    list_parser.add_argument('days', type=int, nargs='?', default=7, help='Number of days to show (default: 7)')
    list_parser.add_argument('--start', help='Start date (default: today)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    editor = CalendarEditor()

    if args.command == 'update-note':
        if editor.update_note(args.date, args.note):
            if not args.no_regen:
                editor.regenerate()
    elif args.command == 'update-title':
        if editor.update_title(args.date, args.title):
            if not args.no_regen:
                editor.regenerate()
    elif args.command == 'list':
        editor.list_workouts(args.days, args.start)


if __name__ == '__main__':
    main()
