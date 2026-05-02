"""
Strava Webhook with DUAL FORM SUPPORT
======================================

This version pushes activities to BOTH the original form AND the enhanced v2 form.
This allows safe testing of the new form without affecting existing data.

To use:
1. Create the enhanced form in Fulcrum (import activities-enhanced-v2.fulcrumapp)
2. Add FULCRUM_FORM_ID_V2 to your .env file with the new form's ID
3. Set ENABLE_DUAL_FORM=true in .env
4. Update run_gunicorn_service.sh to use this file instead of strava_webhook.py
5. Restart the service: servrestart

To switch back to single form:
- Set ENABLE_DUAL_FORM=false or remove from .env
"""

from flask import Flask, request, jsonify
import requests
import polyline
import os
import json
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# --- OAuth Exchange Endpoint ---
@app.route('/exchange_token')
def exchange_token():
    code = request.args.get('code')
    if not code:
        return "No code provided", 400
    client_id = os.environ.get('STRAVA_CLIENT_ID')
    client_secret = os.environ.get('STRAVA_CLIENT_SECRET')
    token_exchange_redirect_uri = os.environ.get('CALLBACK_URL')

    if not token_exchange_redirect_uri:
        return "CALLBACK_URL not set in environment", 500

    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': token_exchange_redirect_uri
        }
    )
    if resp.status_code != 200:
        return f"Token exchange failed: {resp.text}", 400
    token_data = resp.json()
    # Save to .strava-tokens.json
    with open('.strava-tokens.json', 'w') as f:
        json.dump(token_data, f)
    return jsonify({"success": True, "token_data": token_data})

# --- Utility functions to read secrets/config ---

def read_strava_tokens():
    if not os.path.isfile('.strava-tokens.json'):
        raise Exception("Token file .strava-tokens.json not found!")
    with open('.strava-tokens.json') as f:
        content = f.read().strip()
        if not content:
            raise Exception(".strava-tokens.json is empty!")
        return json.loads(content)

def write_strava_tokens(tokens):
    with open('.strava-tokens.json', 'w') as f:
        json.dump(tokens, f)

def get_valid_access_token(max_retries=3):
    """Get a valid access token, refreshing if necessary."""
    for attempt in range(max_retries):
        try:
            tokens = read_strava_tokens()
            current_time = time.time()

            # If token is still valid for at least 5 minutes, return it
            if current_time < tokens.get('expires_at', 0) - 300:
                return tokens['access_token']

            print(f"Access token expired or expiring soon. Refreshing (attempt {attempt + 1}/{max_retries})...")

            # Prepare refresh request
            refresh_data = {
                'client_id': os.environ.get("STRAVA_CLIENT_ID"),
                'client_secret': os.environ.get("STRAVA_CLIENT_SECRET"),
                'grant_type': 'refresh_token',
                'refresh_token': tokens.get('refresh_token')
            }

            # Make the refresh request with timeout
            resp = requests.post(
                "https://www.strava.com/oauth/token",
                data=refresh_data,
                timeout=10
            )

            # Check for successful response
            if resp.status_code == 200:
                new_tokens = resp.json()
                tokens.update({
                    'access_token': new_tokens['access_token'],
                    'refresh_token': new_tokens.get('refresh_token', tokens['refresh_token']),
                    'expires_at': new_tokens['expires_at'],
                    'expires_in': new_tokens['expires_in']
                })
                write_strava_tokens(tokens)
                print("Successfully refreshed access token")
                return tokens['access_token']

            # Handle specific error cases
            elif resp.status_code in [400, 401]:
                error_msg = resp.json().get('message', 'Unknown error')
                if 'Invalid refresh token' in error_msg or 'Authorization Error' in error_msg:
                    print("Refresh token is invalid. Manual re-authentication required.")
                    break
                print(f"Token refresh failed (attempt {attempt + 1}): {error_msg}")
            else:
                print(f"Unexpected status code {resp.status_code} during token refresh")

        except requests.exceptions.RequestException as e:
            print(f"Network error during token refresh (attempt {attempt + 1}): {str(e)}")
        except json.JSONDecodeError:
            print(f"Invalid JSON response during token refresh (attempt {attempt + 1})")
        except KeyError as e:
            print(f"Missing expected key in token response (attempt {attempt + 1}): {str(e)}")
            break

        # Exponential backoff before retry
        if attempt < max_retries - 1:
            backoff = 2 ** attempt
            print(f"Retrying in {backoff} seconds...")
            time.sleep(backoff)

    # If we get here, all retries failed
    error_msg = "Failed to refresh access token after maximum retries. Manual intervention required."
    print(error_msg)
    raise Exception(error_msg)

# Configuration for dual form support
FULCRUM_FORM_ID = os.environ.get("FULCRUM_FORM_ID")  # Original form
FULCRUM_FORM_ID_V2 = os.environ.get("FULCRUM_FORM_ID_V2")  # New enhanced form
ENABLE_DUAL_FORM = os.environ.get("ENABLE_DUAL_FORM", "false").lower() == "true"

def fetch_activity(activity_id, access_token):
    url = f"https://www.strava.com/api/v3/activities/{activity_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Error fetching activity: {resp.status_code}")
        print(resp.text)
        return None

def get_geojson_linestring(activity):
    poly = activity.get('map', {}).get('summary_polyline')
    if not poly:
        print("No polyline found in activity.")
        return None
    points = polyline.decode(poly)
    coordinates = [[lon, lat] for lat, lon in points]
    return {
        "type": "LineString",
        "coordinates": coordinates
    }

def meters_to_miles(meters):
    if meters is None:
        return None
    miles = meters / 1609.344
    return round(miles, 2)

def meters_to_feet(meters):
    if meters is None:
        return None
    return round(meters * 3.28084, 1)

def celsius_to_fahrenheit(c):
    if c is None:
        return None
    return round((c * 9/5) + 32, 1)

def seconds_per_mile(activity):
    """Calculate formatted pace string (MM:SS min/mi)"""
    distance_miles = meters_to_miles(activity.get("distance", 0))
    moving_time = activity.get("moving_time", 0)
    if distance_miles and distance_miles > 0:
        pace_sec = moving_time / distance_miles
        minutes = int(pace_sec // 60)
        seconds = int(pace_sec % 60)
        return f"{minutes}:{seconds:02d} min/mi"
    return None

def pace_seconds_per_mile(activity):
    """Calculate raw pace value in seconds per mile (for NumberField calculations)"""
    distance_miles = meters_to_miles(activity.get("distance", 0))
    moving_time = activity.get("moving_time", 0)
    if distance_miles and distance_miles > 0:
        return round(moving_time / distance_miles, 1)
    return None

def round_or_none(value):
    if value is None:
        return None
    return round(value)

def seconds_to_hms(seconds):
    if seconds is None:
        return None
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:02d}"

def determine_status_from_title(title, activity_type):
    """Determine status field value based on activity title and type.

    Args:
        title: Activity name from Strava
        activity_type: Activity type from Strava (e.g., "Run", "Ride")

    Returns:
        str: Status value (trail, road, strength, yoga, hike) or None
    """
    if not title:
        return None

    title_lower = title.lower()

    # Check title for keywords (case insensitive)
    if "trail run" in title_lower or "trail" in title_lower:
        return "trail"
    elif "strength" in title_lower or "weight" in title_lower:
        return "strength"
    elif "yoga" in title_lower:
        return "yoga"
    elif "hike" in title_lower or "hiking" in title_lower:
        return "hike"
    elif "run" in title_lower or activity_type == "Run":
        return "road"  # Default run to road if not trail
    elif "ride" in title_lower or activity_type == "Ride":
        return "ride"

    # Default based on Strava activity type
    type_mapping = {
        "TrailRun": "trail",
        "Run": "road",
        "Ride": "ride",
        "VirtualRide": "ride",
        "Workout": "strength",
        "WeightTraining": "strength",
        "Yoga": "yoga",
        "Hike": "hike",
        "Walk": "hike"
    }

    return type_mapping.get(activity_type)

def determine_gear_from_status(status):
    """Determine default gear/shoes based on activity status.

    Args:
        status: Activity status (trail, road, strength, yoga, hike, ride)

    Returns:
        str: Gear choice value or None
    """
    if not status:
        return None

    # Map status to default shoe/gear
    gear_mapping = {
        "trail": "speedgoat5_red2",  # Hoka Speedgoat 5 - Red 2
        "road": "bondi74",            # Hoka Bondi 7.4
        "hike": "speedgoat5_red2",    # Use trail shoes for hiking
        # No defaults for strength, yoga, ride (can be set manually)
    }

    return gear_mapping.get(status)

def build_fulcrum_payload_v1(activity, geojson):
    """Build payload for ORIGINAL form (backward compatible)"""
    form_values = {
        "7980": activity.get("name"),
        "2d48": activity.get("start_date_local", "")[:10],
        "3200": activity.get("type"),
        "9000": meters_to_miles(activity.get("distance")),
        "b890": round_or_none(activity.get("calories")),
        "1acf": seconds_per_mile(activity),
        "2050": round_or_none(activity.get("average_heartrate")),
        "4c8d": round_or_none(activity.get("max_heartrate")),
        "cca0": activity.get("start_date_local", "")[11:19],
        "0880": seconds_to_hms(activity.get("elapsed_time")),
        "2180": seconds_to_hms(activity.get("moving_time")),
        "e2d0": activity.get("description"),
        "4840": round_or_none(meters_to_feet(activity.get("total_elevation_gain"))),
        "d000": round_or_none(meters_to_feet(activity.get("elev_low"))),
        "6767": round_or_none(meters_to_feet(activity.get("elev_high"))),
        "3350": celsius_to_fahrenheit(activity.get("average_temp")),
        "25a0": str(activity.get("id"))  # Strava Activity ID
    }
    # Convert all non-None values to strings
    form_values = {k: str(v) for k, v in form_values.items() if v is not None}
    return {
        "record": {
            "geometry": geojson,
            "form_values": form_values
        }
    }

def build_fulcrum_payload_v2(activity, geojson):
    """Build payload for ENHANCED v2 form with new fields and proper types"""

    # Determine status from title
    activity_status = determine_status_from_title(
        activity.get("name"),
        activity.get("type")
    )

    # Determine default gear based on status
    default_gear = determine_gear_from_status(activity_status)

    # Use Strava gear_id if available, otherwise use our default
    strava_gear = activity.get("gear_id")
    selected_gear = default_gear  # Use our smart default

    form_values = {
        # Basic info
        "7980": activity.get("name"),                          # Title
        "2d48": activity.get("start_date_local", "")[:10],     # Date
        "3200": activity.get("type"),                          # Activity Type
        "e2d0": activity.get("description"),                   # Notes
        "cca0": activity.get("start_date_local", "")[11:19],   # Start Time
        "25a0": str(activity.get("id")),                       # Strava Activity ID

        # Distance & Pace (NumberFields in v2)
        "9000": meters_to_miles(activity.get("distance")),    # Distance (miles)
        "a002": pace_seconds_per_mile(activity),               # Pace (seconds/mile) - raw for calculations (HIDDEN)
        "a026": activity.get("max_speed"),                     # Max Speed (m/s) - for fastest pace calc (HIDDEN)
        # Note: 1acf (avg_moving_pace) and a025 (fastest_pace) are CalculatedFields in v2, auto-calculated

        # Time fields (NumberFields + CalculatedFields in v2)
        "a006": activity.get("moving_time"),                   # Moving Time (seconds) - raw (HIDDEN)
        "a007": activity.get("elapsed_time"),                  # Elapsed Time (seconds) - raw (HIDDEN)
        # Note: 2180 and 0880 are CalculatedFields in v2, auto-calculated

        # Heart Rate (NumberFields in v2)
        "2050": round_or_none(activity.get("average_heartrate")),  # Average HR
        "4c8d": round_or_none(activity.get("max_heartrate")),      # Max HR
        # Note: a010 (hr_zone) is a CalculatedField in v2, auto-calculated

        # Power & Cadence (NEW in v2)
        "a012": round_or_none(activity.get("average_cadence")),           # Average Cadence
        "a013": round_or_none(activity.get("average_watts")),             # Average Watts
        "a014": round_or_none(activity.get("max_watts")),                 # Max Watts
        "a015": round_or_none(activity.get("weighted_average_watts")),    # Weighted Avg Watts

        # Calories & Effort (NumberFields in v2)
        "b890": round_or_none(activity.get("calories")),       # Calories
        "a018": round_or_none(activity.get("suffer_score")),   # Suffer Score / Relative Effort
        # Note: a017 (calories_per_mile), a019 (effort_score) are CalculatedFields in v2

        # Elevation (NumberFields in v2)
        "4840": meters_to_feet(activity.get("total_elevation_gain")),  # Total Elevation Gain (ft)
        "d000": meters_to_feet(activity.get("elev_low")),              # Min Elevation (ft)
        "6767": meters_to_feet(activity.get("elev_high")),             # Max Elevation (ft)
        # Note: a020 (elevation_gain_per_mile) is a CalculatedField in v2

        # Notes & Details
        "3350": celsius_to_fahrenheit(activity.get("average_temp")),  # Avg Temp (°F)
        "a022": activity.get("device_name"),                           # Device Name (NEW)
        "a023": selected_gear,                                         # Shoes/Gear (auto-selected based on activity type)
        # Pattern Type (be00) and Garmin Link (2b00) can be added manually in Fulcrum
    }

    # Convert non-None values to strings (Fulcrum API expects strings)
    form_values = {k: str(v) for k, v in form_values.items() if v is not None}

    payload = {
        "record": {
            "geometry": geojson,
            "form_values": form_values
        }
    }

    # Set status field if determined
    if activity_status:
        payload["record"]["status"] = activity_status
        print(f"   Auto-setting status to: {activity_status}")

    # Log gear selection
    if selected_gear:
        gear_labels = {
            "speedgoat5_red2": "Hoka Speedgoat 5 - Red 2",
            "bondi74": "Hoka Bondi 7.4"
        }
        gear_label = gear_labels.get(selected_gear, selected_gear)
        print(f"   Auto-selecting gear: {gear_label}")

    return payload

def read_fulcrum_token():
    return os.environ.get("FULCRUM_API_TOKEN")

def activity_exists_in_fulcrum(activity_id, form_id=None):
    """Check if an activity already exists in Fulcrum."""
    try:
        api_token = os.environ.get("FULCRUM_API_TOKEN")
        if not form_id:
            form_id = os.environ.get("FULCRUM_FORM_ID")

        if not api_token or not form_id:
            print("Warning: Missing Fulcrum credentials, skipping duplicate check")
            return False

        headers = {
            "Accept": "application/json",
            "X-ApiToken": api_token
        }

        page = 1
        per_page = 100

        while True:
            params = {
                "form_id": form_id,
                "page": page,
                "per_page": per_page
            }

            url = "https://api.fulcrumapp.com/api/v2/records.json"
            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                print(f"Warning: Error checking Fulcrum page {page}: {response.status_code}")
                return False

            data = response.json()
            records = data.get("records", [])

            # Check this page for the activity_id
            for record in records:
                form_values = record.get("form_values", {})
                if form_values.get("25a0") == str(activity_id):
                    return True

            # If we got fewer records than per_page, we've reached the end
            if len(records) < per_page:
                break

            page += 1

        return False

    except Exception as e:
        print(f"Warning: Error checking for duplicates in Fulcrum: {str(e)}")
        return False

def create_fulcrum_record(payload, form_id, form_name=""):
    """Create a record in Fulcrum."""
    api_token = read_fulcrum_token()
    url = "https://api.fulcrumapp.com/api/v2/records.json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-ApiToken": api_token
    }
    payload['record']['form_id'] = form_id

    print(f"\n==== Creating Fulcrum Record{' (' + form_name + ')' if form_name else ''} ====")
    print(f"Form ID: {form_id}")
    print("Payload preview:", json.dumps(payload['record']['form_values'], indent=2)[:500])

    resp = requests.post(url, headers=headers, json=payload)
    print(f"Fulcrum response{' (' + form_name + ')' if form_name else ''}: {resp.status_code}")

    try:
        resp_json = resp.json()
        if resp.status_code == 201:
            print(f"✓ Successfully created record in {form_name or 'form'}")
            record_id = resp_json.get('record', {}).get('id')
            if record_id:
                print(f"  Record ID: {record_id}")
        else:
            print(f"✗ Error creating record in {form_name or 'form'}")
            if 'record' in resp_json and 'errors' in resp_json['record']:
                print(f"  Errors: {resp_json['record']['errors']}")
    except Exception as e:
        print(f"Error parsing Fulcrum response: {e}")
        print(resp.text[:500])

    return resp

@app.route('/strava-webhook', methods=['GET', 'POST'])
def strava_webhook():
    if request.method == 'GET':
        return jsonify({
            "hub.challenge": request.args.get("hub.challenge")
        })

    if request.method == 'POST':
        event = request.json
        print("Received webhook event:")
        print(event)

        if event['object_type'] == 'activity' and event['aspect_type'] == 'create':
            activity_id = event['object_id']
            print(f"Fetching details for activity ID: {activity_id}")

            # Check if activity already exists in original form
            if activity_exists_in_fulcrum(activity_id, FULCRUM_FORM_ID):
                print(f"Activity {activity_id} already exists in original form - skipping")
                return '', 200

            # Fetch activity details
            access_token = get_valid_access_token()
            activity = fetch_activity(activity_id, access_token)

            if not activity:
                print("Failed to fetch activity details")
                return '', 200

            geojson = get_geojson_linestring(activity)

            # Always submit to original form
            print("\n" + "="*60)
            print("SUBMITTING TO ORIGINAL FORM")
            print("="*60)
            payload_v1 = build_fulcrum_payload_v1(activity, geojson)
            create_fulcrum_record(payload_v1, FULCRUM_FORM_ID, "Original Form")

            # Optionally submit to v2 form
            if ENABLE_DUAL_FORM and FULCRUM_FORM_ID_V2:
                print("\n" + "="*60)
                print("SUBMITTING TO ENHANCED V2 FORM")
                print("="*60)

                # Check if already exists in v2 form
                if activity_exists_in_fulcrum(activity_id, FULCRUM_FORM_ID_V2):
                    print(f"Activity {activity_id} already exists in v2 form - skipping")
                else:
                    payload_v2 = build_fulcrum_payload_v2(activity, geojson)
                    create_fulcrum_record(payload_v2, FULCRUM_FORM_ID_V2, "Enhanced v2 Form")
            elif ENABLE_DUAL_FORM and not FULCRUM_FORM_ID_V2:
                print("\n⚠️  ENABLE_DUAL_FORM is true but FULCRUM_FORM_ID_V2 is not set!")
                print("   Skipping v2 form submission.")
            else:
                print("\n📝 Dual form submission disabled (ENABLE_DUAL_FORM=false)")

        return '', 200

if __name__ == '__main__':
    print("\n" + "="*60)
    print("STRAVA WEBHOOK - DUAL FORM MODE")
    print("="*60)
    print(f"Original Form ID: {FULCRUM_FORM_ID}")
    print(f"Enhanced v2 Form ID: {FULCRUM_FORM_ID_V2 or 'Not configured'}")
    print(f"Dual Form Enabled: {ENABLE_DUAL_FORM}")
    print("="*60 + "\n")
    app.run(port=5055)
