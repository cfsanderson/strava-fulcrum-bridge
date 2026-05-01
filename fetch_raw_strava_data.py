#!/usr/bin/env python3
"""
Fetch raw Strava activity data and save to JSON file.
This helps with understanding the Strava API response format for form design.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from strava_webhook import get_valid_access_token, fetch_activity

def fetch_recent_activities(count=30, days_back=30):
    """Fetch recent activities from Strava (summary data)."""
    access_token = get_valid_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}

    # Calculate the 'after' timestamp for filtering
    after_date = datetime.now() - timedelta(days=days_back)
    after_timestamp = int(after_date.timestamp())

    params = {
        'per_page': min(count, 200),
        'page': 1,
        'after': after_timestamp
    }

    response = requests.get(
        'https://www.strava.com/api/v3/athlete/activities',
        headers=headers,
        params=params
    )

    if response.status_code != 200:
        print(f"Error fetching activities: {response.status_code}")
        print(response.text)
        return []

    return response.json()

def main():
    """Fetch raw data and save to JSON file."""
    print("Fetching raw Strava activity data...")

    # Fetch summary activities
    print("Step 1: Fetching activity list (summary data)...")
    activities_summary = fetch_recent_activities(count=30, days_back=30)
    print(f"Found {len(activities_summary)} activities")

    # Fetch detailed data for each activity
    print("\nStep 2: Fetching detailed data for each activity...")
    access_token = get_valid_access_token()
    activities_detailed = []

    for i, activity in enumerate(activities_summary[:5], 1):  # Get detailed data for first 5
        activity_id = activity['id']
        print(f"  [{i}/5] Fetching details for activity {activity_id} ({activity['name']})...")
        detailed = fetch_activity(activity_id, access_token)
        activities_detailed.append(detailed)

    # Prepare output data
    output_data = {
        "fetch_date": datetime.now().isoformat(),
        "summary": "Raw Strava API data for form design reference",
        "activities_summary_count": len(activities_summary),
        "activities_detailed_count": len(activities_detailed),
        "activities_summary": activities_summary,
        "activities_detailed": activities_detailed,
        "api_documentation": {
            "summary_endpoint": "GET /athlete/activities",
            "detailed_endpoint": "GET /activities/{id}",
            "docs_url": "https://developers.strava.com/docs/reference/#api-Activities"
        }
    }

    # Save to file
    output_file = "/home/caleb/Projects/files/strava_raw_data.json"
    print(f"\nStep 3: Saving to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"✓ Successfully saved raw Strava data to {output_file}")
    print(f"\nSummary:")
    print(f"  - {len(activities_summary)} activity summaries")
    print(f"  - {len(activities_detailed)} detailed activity records")
    print(f"  - File size: {os.path.getsize(output_file) / 1024:.2f} KB")
    print(f"\nYou can now review the raw JSON to redesign your Fulcrum form.")

if __name__ == "__main__":
    main()
