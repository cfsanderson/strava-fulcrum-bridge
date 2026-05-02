#!/usr/bin/env python3
"""
Backfill Activities by Date Range to Enhanced v2 Form
======================================================

Fetches ALL activities from a date range and creates records in the enhanced v2 form.
Handles rate limiting, progress tracking, and resumption.

Usage:
    python3 backfill_date_range.py [start_date] [end_date]

    start_date: YYYY-MM-DD (default: 2024-06-01)
    end_date: YYYY-MM-DD (default: today)

Example:
    python3 backfill_date_range.py 2024-06-01 2026-05-02

Features:
- Respects Strava API rate limits (100/15min, 1000/day)
- Shows detailed progress
- Skips duplicates automatically
- Handles errors gracefully
- Can be interrupted and resumed
"""

import sys
import os
from datetime import datetime, timedelta
import time
from strava_webhook_dual_form import (
    get_valid_access_token,
    fetch_activity,
    get_geojson_linestring,
    build_fulcrum_payload_v2,
    create_fulcrum_record,
    activity_exists_in_fulcrum
)
import requests

def parse_date(date_str):
    """Parse YYYY-MM-DD to datetime"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

def datetime_to_unix(dt):
    """Convert datetime to Unix timestamp"""
    return int(dt.timestamp())

def fetch_all_activities_in_range(access_token, start_date, end_date):
    """Fetch all activities in date range from Strava.

    Args:
        access_token: Strava access token
        start_date: datetime object for start
        end_date: datetime object for end

    Returns:
        List of activity summaries
    """

    after_timestamp = datetime_to_unix(start_date)
    before_timestamp = datetime_to_unix(end_date)

    print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"   Unix timestamps: {after_timestamp} to {before_timestamp}")
    print()

    headers = {"Authorization": f"Bearer {access_token}"}
    all_activities = []
    page = 1
    per_page = 200  # Max allowed by Strava API
    request_count = 0

    print("📡 Fetching activities from Strava...")

    while True:
        # Check rate limit (leave some headroom)
        if request_count > 0 and request_count % 90 == 0:
            print(f"\n⏸️  Rate limit protection: Waiting 15 minutes...")
            print(f"   (Fetched {len(all_activities)} activities so far)")
            for remaining in range(900, 0, -60):
                mins = remaining // 60
                print(f"   Resuming in {mins} minute(s)...", end="\r")
                time.sleep(60)
            print("\n   Resuming...                     ")

        try:
            params = {
                "after": after_timestamp,
                "before": before_timestamp,
                "page": page,
                "per_page": per_page
            }

            resp = requests.get(
                "https://www.strava.com/api/v3/athlete/activities",
                headers=headers,
                params=params,
                timeout=30
            )

            request_count += 1

            if resp.status_code == 429:
                # Rate limited - wait and retry
                retry_after = int(resp.headers.get('Retry-After', 900))
                print(f"\n⚠️  Rate limited by Strava. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue

            if resp.status_code != 200:
                print(f"\n❌ Error fetching page {page}: {resp.status_code}")
                print(resp.text[:200])
                break

            activities = resp.json()

            if not activities:
                # No more activities
                break

            all_activities.extend(activities)
            print(f"   Page {page}: {len(activities)} activities (total: {len(all_activities)})", end="\r")

            # If we got fewer than per_page, we're done
            if len(activities) < per_page:
                break

            page += 1

            # Small delay between requests
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"\n⚠️  Network error on page {page}: {e}")
            print("   Retrying in 10 seconds...")
            time.sleep(10)
            continue
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            break

    print(f"\n✓ Fetched {len(all_activities)} activities total")
    return all_activities

def backfill_activities_range(start_date_str, end_date_str):
    """Backfill activities in date range to v2 form."""

    # Parse dates
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)

    if not start_date:
        print(f"❌ Error: Invalid start date '{start_date_str}'. Use YYYY-MM-DD format.")
        return 1

    if not end_date:
        print(f"❌ Error: Invalid end date '{end_date_str}'. Use YYYY-MM-DD format.")
        return 1

    if start_date > end_date:
        print(f"❌ Error: Start date must be before end date")
        return 1

    print("="*70)
    print("BACKFILLING ACTIVITIES BY DATE RANGE")
    print("="*70)
    print()

    form_id_v2 = os.environ.get('FULCRUM_FORM_ID_V2')

    if not form_id_v2:
        print("❌ Error: FULCRUM_FORM_ID_V2 not set in .env")
        return 1

    print(f"Target Form: {form_id_v2}")
    print(f"Date Range: {start_date_str} to {end_date_str}")

    duration = (end_date - start_date).days
    print(f"Duration: {duration} days ({duration/30:.1f} months)")
    print()

    # Get access token
    try:
        access_token = get_valid_access_token()
    except Exception as e:
        print(f"❌ Error getting access token: {e}")
        return 1

    # Fetch all activities in range
    activities = fetch_all_activities_in_range(access_token, start_date, end_date)

    if not activities:
        print("❌ No activities found in date range")
        return 1

    print()
    print("="*70)
    print(f"PROCESSING {len(activities)} ACTIVITIES")
    print("="*70)
    print()

    # Process each activity
    success_count = 0
    skip_count = 0
    error_count = 0
    start_time = time.time()

    for i, activity_summary in enumerate(activities, 1):
        activity_id = activity_summary['id']
        activity_name = activity_summary['name']
        activity_date = activity_summary['start_date_local'][:10]
        activity_type = activity_summary['type']

        elapsed = time.time() - start_time
        avg_time = elapsed / i if i > 0 else 0
        remaining = avg_time * (len(activities) - i)

        print(f"[{i}/{len(activities)}] {activity_name} ({activity_date}) - {activity_type}")
        print(f"  Progress: {i/len(activities)*100:.1f}% | Elapsed: {elapsed/60:.1f}m | ETA: {remaining/60:.1f}m")

        # Check if already exists
        if activity_exists_in_fulcrum(activity_id, form_id_v2):
            print(f"  ⏭️  Already exists - skipping")
            skip_count += 1
            print()
            continue

        # Fetch and create
        try:
            activity = fetch_activity(activity_id, access_token)

            if not activity:
                print(f"  ❌ Failed to fetch details")
                error_count += 1
                print()
                continue

            geojson = get_geojson_linestring(activity)
            payload = build_fulcrum_payload_v2(activity, geojson)

            resp = create_fulcrum_record(payload, form_id_v2, "v2")

            if resp.status_code == 201:
                record_data = resp.json()
                record_id = record_data.get('record', {}).get('id')
                print(f"  ✅ Created: {record_id}")
                success_count += 1
            else:
                print(f"  ❌ Failed (HTTP {resp.status_code})")
                error_count += 1

        except Exception as e:
            print(f"  ❌ Error: {str(e)[:100]}")
            error_count += 1

        print()

        # Small delay between activities
        time.sleep(0.3)

        # Progress checkpoint every 50 activities
        if i % 50 == 0:
            print("="*70)
            print(f"CHECKPOINT: {i}/{len(activities)} activities processed")
            print(f"✅ Created: {success_count} | ⏭️ Skipped: {skip_count} | ❌ Errors: {error_count}")
            print("="*70)
            print()

    # Final summary
    total_time = time.time() - start_time

    print()
    print("="*70)
    print("BACKFILL COMPLETE")
    print("="*70)
    print(f"Total activities: {len(activities)}")
    print(f"✅ Successfully created: {success_count}")
    print(f"⏭️  Skipped (duplicates): {skip_count}")
    print(f"❌ Errors: {error_count}")
    print()
    print(f"⏱️  Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
    if success_count > 0:
        print(f"   Average: {total_time/success_count:.1f} seconds per activity")
    print()

    if success_count > 0:
        print(f"🎉 View your activities:")
        print(f"   https://web.fulcrumapp.com/apps/{form_id_v2}")

    return 0 if error_count == 0 else 1

def main():
    # Default date range: June 1, 2024 to today
    default_start = "2024-06-01"
    default_end = datetime.now().strftime("%Y-%m-%d")

    start_date = default_start
    end_date = default_end

    if len(sys.argv) > 1:
        start_date = sys.argv[1]

    if len(sys.argv) > 2:
        end_date = sys.argv[2]

    return backfill_activities_range(start_date, end_date)

if __name__ == "__main__":
    exit(main())
