#!/usr/bin/env python3
"""
Import training plan CSV into SQLite database.
Usage: python3 calendar/import_plan.py path/to/phase1_training_plan.csv
"""

import sqlite3
import csv
import sys
import os
import re
from datetime import datetime

def parse_duration(duration_str):
    """Extract minutes from '30-35min' or '45min' format."""
    if not duration_str or duration_str == '0':
        return None
    match = re.search(r'(\d+)', duration_str)
    return int(match.group(1)) if match else None

def parse_distance(distance_str):
    """Convert distance string to float, handling ranges."""
    if not distance_str or distance_str == '0':
        return None
    # For ranges like "3-4", take the midpoint
    if '-' in distance_str:
        parts = distance_str.split('-')
        return (float(parts[0]) + float(parts[1])) / 2
    return float(distance_str)

def import_training_plan(csv_path, db_path='training_calendar/training_plan.db'):
    """Import CSV training plan into database."""

    # Ensure the database directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS planned_workouts (
            id TEXT PRIMARY KEY,
            date DATE NOT NULL,
            workout_type TEXT NOT NULL,
            details TEXT,
            duration_minutes INTEGER,
            distance_miles REAL,
            notes TEXT,
            start_time TIME DEFAULT '06:30:00',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS completed_activities (
            id TEXT PRIMARY KEY,
            planned_workout_id TEXT,
            date DATE NOT NULL,
            activity_type TEXT,
            distance_miles REAL,
            duration_minutes INTEGER,
            avg_pace TEXT,
            avg_hr INTEGER,
            max_hr INTEGER,
            elevation_gain_ft INTEGER,
            strava_url TEXT,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (planned_workout_id) REFERENCES planned_workouts(id)
        );

        CREATE INDEX IF NOT EXISTS idx_planned_date ON planned_workouts(date);
        CREATE INDEX IF NOT EXISTS idx_completed_date ON completed_activities(date);
    """)

    # Import CSV
    count = 0
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse date (MM-DD format to YYYY-MM-DD)
            month, day = row['Date'].split('-')
            date_str = f"2026-{month.zfill(2)}-{day.zfill(2)}"

            # Create unique ID
            workout_type_slug = row['Workout Type'].lower().replace(' ', '-').replace('(', '').replace(')', '')
            workout_id = f"{date_str}-{workout_type_slug}"

            # Parse duration and distance
            duration = parse_duration(row['Duration'])
            distance = parse_distance(row['Distance (mi)'])

            cursor.execute("""
                INSERT OR REPLACE INTO planned_workouts
                (id, date, workout_type, details, duration_minutes, distance_miles, notes, start_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workout_id,
                date_str,
                row['Workout Type'],
                row['Details'],
                duration,
                distance,
                row['Notes'],
                '06:30:00'
            ))
            count += 1

    conn.commit()
    total = cursor.execute("SELECT COUNT(*) FROM planned_workouts").fetchone()[0]
    print(f"✓ Imported {count} rows")
    print(f"✓ Total planned workouts in database: {total}")
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 calendar/import_plan.py path/to/phase1_training_plan.csv")
        sys.exit(1)

    import_training_plan(sys.argv[1])
