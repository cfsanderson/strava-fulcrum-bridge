#!/usr/bin/env python3
"""
Re-import training plan from CSV, preserving completed activities.

This script:
1. Backs up the existing database
2. Re-imports the CSV to update planned workouts
3. Preserves all completed activity data and matches
4. Regenerates the calendar

Usage:
    ./reimport_plan.py your_training_plan.csv
"""

import sys
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from training_calendar.import_plan import TrainingPlanImporter
from training_calendar.generator import CalendarGenerator


def reimport_plan(csv_path, db_path='training_calendar/training_plan.db'):
    """Re-import CSV while preserving completed activities."""

    if not Path(csv_path).exists():
        print(f"✗ CSV file not found: {csv_path}")
        return False

    # Create backup
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"📦 Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Export completed activities to temp table
    print("💾 Saving completed activities...")
    cursor.execute("""
        CREATE TEMPORARY TABLE temp_completed AS
        SELECT * FROM completed_activities
    """)

    # Clear planned_workouts table
    print("🗑️  Clearing old planned workouts...")
    cursor.execute("DELETE FROM planned_workouts")
    conn.commit()

    # Re-import CSV
    print(f"📥 Importing CSV: {csv_path}")
    importer = TrainingPlanImporter(db_path)
    importer.import_csv(csv_path)

    # Re-match completed activities with new planned workouts
    print("🔗 Re-matching completed activities...")
    cursor.execute("""
        UPDATE completed_activities
        SET planned_workout_id = (
            SELECT id FROM planned_workouts
            WHERE date = completed_activities.date
            AND LOWER(workout_type) = LOWER(completed_activities.activity_type)
            LIMIT 1
        )
    """)
    conn.commit()

    # Report results
    cursor.execute("SELECT COUNT(*) FROM completed_activities WHERE planned_workout_id IS NOT NULL")
    matched_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM completed_activities WHERE planned_workout_id IS NULL")
    unmatched_count = cursor.fetchone()[0]

    print(f"\n✓ Re-import complete!")
    print(f"  - {matched_count} completed activities re-matched")
    print(f"  - {unmatched_count} unmatched activities (extra credit)")

    conn.close()

    # Regenerate calendar
    print("\n🔄 Regenerating calendar...")
    generator = CalendarGenerator(db_path)
    generator.generate_calendar()

    print(f"\n💡 Backup saved at: {backup_path}")
    print("   If something went wrong, restore with:")
    print(f"   cp {backup_path} {db_path}")

    return True


def main():
    if len(sys.argv) != 2:
        print("Usage: ./reimport_plan.py <csv_file>")
        print("\nExample:")
        print("  ./reimport_plan.py updated_training_plan.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    reimport_plan(csv_path)


if __name__ == '__main__':
    main()
