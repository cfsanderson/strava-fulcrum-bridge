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
import argparse
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

def fetch_recent_activities(count=1, before=None, after=None, page=1, per_page=30):
    """Fetch recent activities from Strava.
    
    Args:
        count: Number of activities to fetch (max 200)
        before: Unix timestamp for activities before this time
        after: Unix timestamp for activities after this time
        page: Page number to fetch (for pagination)
        per_page: Number of activities per page (max 200)
    """
    access_token = get_valid_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Build query parameters
    params = {
        'per_page': min(per_page, 200),  # Strava max is 200 per page
        'page': page
    }
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
    
    activities = response.json()
    
    # If we didn't get enough activities and there might be more, fetch next page
    if len(activities) < count and len(activities) == per_page:
        next_page = fetch_recent_activities(
            count - len(activities),
            before,
            after,
            page + 1,
            per_page
        )
        activities.extend(next_page)
    
    # Return only the requested number of activities, most recent first
    return activities[:count]

def activity_exists_in_fulcrum(activity_id):
    """Check if an activity already exists in Fulcrum.
    
    Args:
        activity_id: Strava activity ID to check
        
    Returns:
        bool: True if activity exists, False otherwise
    """
    # TODO: Implement this function based on your Fulcrum schema
    # You'll need to query your Fulcrum form to check if the activity ID exists
    # For now, we'll return False to always assume activities don't exist
    return False

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
    
    # First, fetch activities to see what we're working with
    activities = fetch_recent_activities(count=count, after=after_time)
    
    if not activities:
        print("No activities found to sync.")
        return
    
    # Sort activities by date (newest first)
    activities.sort(key=lambda x: x.get('start_date', ''), reverse=True)
    
    print(f"Found {len(activities)} activities to process...")
    
    synced_count = 0
    skipped_count = 0
    
    for i, activity in enumerate(activities, 1):
        activity_id = activity['id']
        activity_name = activity.get('name', 'Unnamed Activity')
        activity_date = activity.get('start_date_local', 'Unknown date')
        
        print(f"\n[{i}/{len(activities)}] Processing: {activity_name} ({activity_date})")
        
        # Check if this activity already exists in Fulcrum
        if activity_exists_in_fulcrum(activity_id):
            print(f"  ✓ Already exists in Fulcrum - skipping")
            skipped_count += 1
            continue
            
        try:
            # Get full activity details
            full_activity = fetch_activity(activity_id, get_valid_access_token())
            if not full_activity:
                print(f"  ✗ Skipping - could not fetch activity details")
                skipped_count += 1
                continue
            
            # Prepare and send to Fulcrum
            geojson = get_geojson_linestring(full_activity)
            payload = build_fulcrum_payload(full_activity, geojson)
            
            print(f"  Sending to Fulcrum...")
            fulcrum_form_id = os.environ.get("FULCRUM_FORM_ID")
            if not fulcrum_form_id:
                print("  ✗ Error: FULCRUM_FORM_ID not found in environment variables")
                skipped_count += 1
                continue
                
            print(f"  Using Fulcrum form ID: {fulcrum_form_id}")
            response = create_fulcrum_record(payload, fulcrum_form_id)
            
            if response and hasattr(response, 'status_code'):
                if response.status_code == 201:
                    print(f"  ✓ Successfully synced to Fulcrum")
                    synced_count += 1
                else:
                    print(f"  ✗ Failed to sync to Fulcrum (Status: {response.status_code})")
                    if hasattr(response, 'text'):
                        print(f"  Response: {response.text}")
                    skipped_count += 1
            else:
                print("  ✗ No valid response received from Fulcrum API")
                skipped_count += 1
            
        except Exception as e:
            print(f"  ✗ Error processing activity: {str(e)}")
            skipped_count += 1
    
    # Print summary
    print("\n=== Sync Summary ===")
    print(f"Total activities processed: {len(activities)}")
    print(f"Successfully synced: {synced_count}")
    print(f"Skipped/duplicate: {skipped_count}")
    if synced_count == 0 and skipped_count > 0:
        print("\nNote: All activities were skipped. This might be because they already exist in Fulcrum.")

def main():
    debug_environment()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Sync Strava activities to Fulcrum')
    parser.add_argument('count', type=int, nargs='?', default=1,
                      help='Number of recent activities to sync (default: 1)')
    parser.add_argument('--days', type=int, default=30,
                      help='Number of days to look back for activities (default: 30)')
    
    args = parser.parse_args()
    
    # Run the sync
    sync_activities(count=args.count, days_back=args.days)

if __name__ == "__main__":
    main()
