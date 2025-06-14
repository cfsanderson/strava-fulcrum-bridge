#!/usr/bin/env python3
"""
Command-line tool to manually sync recent Strava activities to Fulcrum.

Usage:
    python sync_activities.py [number_of_activities]
    python sync_activities.py 5  # Syncs the 5 most recent activities
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

def debug_environment():
    """Print debug information about the environment."""
    print("\n==== Environment Debug ====")
    print(f"Current directory: {os.getcwd()}")
    print(f"Environment file exists: {os.path.exists('.env')}")
    print("FULCRUM_API_TOKEN present:", "FULCRUM_API_TOKEN" in os.environ)
    print("FULCRUM_FORM_ID present:", "FULCRUM_FORM_ID" in os.environ)
    print("STRAVA_CLIENT_ID present:", "STRAVA_CLIENT_ID" in os.environ)
    print("STRAVA_CLIENT_SECRET present:", "STRAVA_CLIENT_SECRET" in os.environ)
    print("STRAVA_REFRESH_TOKEN present:", "STRAVA_REFRESH_TOKEN" in os.environ)

# Load environment variables from .env file
load_dotenv()

from strava_webhook import (
    get_valid_access_token,
    fetch_activity,
    get_geojson_linestring,
    build_fulcrum_payload,
    create_fulcrum_record,
)

def fetch_recent_activities(count=1, before=None, after=None):
    """Fetch recent activities from Strava.
    
    Args:
        count: Number of activities to fetch (max 200)
        before: Unix timestamp for activities before this time
        after: Unix timestamp for activities after this time
    """
    access_token = get_valid_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Build query parameters
    params = {'per_page': min(count, 200)}  # Strava max is 200 per page
    if before:
        params['before'] = before
    if after:
        params['after'] = after
    
    # Make the API request
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

def sync_activities(count=1, days_back=30):
    """Sync recent activities to Fulcrum.
    
    Args:
        count: Number of recent activities to sync (max 200)
        days_back: Only sync activities from the last N days
    """
    # Calculate timestamps
    now = int(datetime.now().timestamp())
    after_time = int((datetime.now() - timedelta(days=days_back)).timestamp())
    
    print(f"Fetching up to {count} activities from the last {days_back} days...")
    activities = fetch_recent_activities(count=count, after=after_time)
    
    if not activities:
        print("No activities found to sync.")
        return
    
    print(f"Found {len(activities)} activities to process...")
    
    for i, activity in enumerate(activities, 1):
        activity_id = activity['id']
        activity_name = activity.get('name', 'Unnamed Activity')
        activity_date = activity.get('start_date_local', 'Unknown date')
        
        print(f"\n[{i}/{len(activities)}] Processing: {activity_name} ({activity_date})")
        
        try:
            # Get full activity details
            full_activity = fetch_activity(activity_id, get_valid_access_token())
            if not full_activity:
                print(f"  Skipping - could not fetch activity details")
                continue
            
            # Prepare and send to Fulcrum
            geojson = get_geojson_linestring(full_activity)
            payload = build_fulcrum_payload(full_activity, geojson)
            
            print(f"  Sending to Fulcrum...")
            fulcrum_form_id = os.environ.get("FULCRUM_FORM_ID")
            if not fulcrum_form_id:
                print("  ✗ Error: FULCRUM_FORM_ID not found in environment variables")
                continue
                
            print(f"  Using Fulcrum form ID: {fulcrum_form_id}")
            response = create_fulcrum_record(payload, fulcrum_form_id)
            
            if response and hasattr(response, 'status_code') and response.status_code == 201:
                print(f"  ✓ Successfully synced to Fulcrum")
            else:
                status = getattr(response, 'status_code', 'No response')
                print(f"  ✗ Failed to sync to Fulcrum (Status: {status})")
                if hasattr(response, 'text'):
                    print(f"  Response: {response.text}")
            
        except Exception as e:
            print(f"  Error processing activity: {str(e)}")

def main():
    debug_environment()
    # Parse command line arguments
    count = 1  # Default to syncing just the most recent activity
    
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
            if count < 1:
                raise ValueError("Count must be at least 1")
        except ValueError as e:
            print(f"Error: {e}")
            print("Usage: python sync_activities.py [number_of_activities]")
            sys.exit(1)
    
    # Run the sync
    sync_activities(count=count)

if __name__ == "__main__":
    main()
