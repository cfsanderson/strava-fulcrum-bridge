#!/usr/bin/env python3
"""
Test script to manually push one activity to the enhanced v2 form
"""

from strava_webhook_dual_form import (
    get_valid_access_token,
    fetch_activity,
    get_geojson_linestring,
    build_fulcrum_payload_v2,
    create_fulcrum_record,
    activity_exists_in_fulcrum
)
import os
from dotenv import load_dotenv

load_dotenv()

def test_v2_form():
    """Test pushing an activity to the v2 form"""

    print("="*60)
    print("TESTING ENHANCED V2 FORM")
    print("="*60)

    # Get form IDs
    form_id_v1 = os.environ.get("FULCRUM_FORM_ID")
    form_id_v2 = os.environ.get("FULCRUM_FORM_ID_V2")

    print(f"\nOriginal Form ID: {form_id_v1}")
    print(f"Enhanced v2 Form ID: {form_id_v2}")

    if not form_id_v2:
        print("\n❌ Error: FULCRUM_FORM_ID_V2 not set in .env")
        return

    # Get the most recent activity
    print("\n📡 Fetching most recent Strava activity...")
    access_token = get_valid_access_token()

    # List activities
    import requests
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers=headers,
        params={"per_page": 1}
    )

    if resp.status_code != 200:
        print(f"❌ Error fetching activities: {resp.status_code}")
        return

    activities = resp.json()
    if not activities:
        print("❌ No activities found")
        return

    activity_summary = activities[0]
    activity_id = activity_summary['id']
    activity_name = activity_summary['name']

    print(f"\n✓ Found activity: {activity_name} (ID: {activity_id})")

    # Check if it already exists in v2 form
    print(f"\n🔍 Checking if activity exists in v2 form...")
    if activity_exists_in_fulcrum(activity_id, form_id_v2):
        print(f"⚠️  Activity already exists in v2 form")
        print(f"   View at: https://web.fulcrumapp.com/apps/{form_id_v2}")

        proceed = input("\n   Force re-create anyway? (y/N): ").strip().lower()
        if proceed != 'y':
            print("   Skipping...")
            return
    else:
        print("✓ Activity not in v2 form yet")

    # Fetch full activity details
    print(f"\n📥 Fetching full activity details...")
    activity = fetch_activity(activity_id, access_token)

    if not activity:
        print("❌ Failed to fetch activity details")
        return

    print(f"✓ Fetched activity data")
    print(f"   Distance: {activity.get('distance', 0) / 1609.344:.2f} mi")
    print(f"   Moving time: {activity.get('moving_time', 0)} sec")
    print(f"   Type: {activity.get('type')}")

    # Get geojson
    print(f"\n🗺️  Converting route to GeoJSON...")
    geojson = get_geojson_linestring(activity)
    if geojson:
        print(f"✓ Route converted ({len(geojson['coordinates'])} points)")
    else:
        print("⚠️  No route data available")

    # Build v2 payload
    print(f"\n📦 Building enhanced v2 payload...")
    payload = build_fulcrum_payload_v2(activity, geojson)

    print(f"✓ Payload built with {len(payload['record']['form_values'])} fields:")
    for key, value in list(payload['record']['form_values'].items())[:5]:
        print(f"   {key}: {value}")
    print(f"   ... and {len(payload['record']['form_values']) - 5} more fields")

    # Create record
    print(f"\n🚀 Submitting to enhanced v2 form...")
    resp = create_fulcrum_record(payload, form_id_v2, "Enhanced v2 Form")

    if resp.status_code == 201:
        record_data = resp.json()
        record_id = record_data.get('record', {}).get('id')
        print(f"\n✅ SUCCESS! Activity created in v2 form")
        print(f"   Record ID: {record_id}")
        print(f"   View at: https://web.fulcrumapp.com/records/{record_id}")
        print(f"   Form: https://web.fulcrumapp.com/apps/{form_id_v2}")

        print(f"\n💡 Now compare with original form:")
        print(f"   https://web.fulcrumapp.com/apps/{form_id_v1}")

    else:
        print(f"\n❌ Failed to create record (HTTP {resp.status_code})")

if __name__ == "__main__":
    test_v2_form()
