from flask import Flask, request, jsonify
import requests
import polyline
import os
import json
import time

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
        return "CALLBACK_URL not set in environment", 500 # Or handle error appropriately

    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': token_exchange_redirect_uri  # THIS IS THE ADDED/MODIFIED LINE
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

def get_valid_access_token():
    tokens = read_strava_tokens()
    if time.time() > tokens['expires_at'] - 60:
        print("Refreshing Strava access token...")
        resp = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": os.environ.get("STRAVA_CLIENT_ID"),
                "client_secret": os.environ.get("STRAVA_CLIENT_SECRET"),
                "grant_type": "refresh_token",
                "refresh_token": tokens['refresh_token']
            }
        )
        if resp.status_code == 200:
            new_tokens = resp.json()
            tokens['access_token'] = new_tokens['access_token']
            tokens['refresh_token'] = new_tokens['refresh_token']
            tokens['expires_at'] = new_tokens['expires_at']
            write_strava_tokens(tokens)
        else:
            print("Failed to refresh token:", resp.text)
            raise Exception("Strava token refresh failed")
    return tokens['access_token']

FULCRUM_FORM_ID = os.environ.get("FULCRUM_FORM_ID")

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
    # Debug: Print the map object to see what Strava returns
    print("Activity map object:", activity.get('map'))
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
    # Use moving_time for average pace, print debug info
    distance_miles = meters_to_miles(activity.get("distance", 0))
    moving_time = activity.get("moving_time", 0)
    elapsed_time = activity.get("elapsed_time", 0)
    print(f"[PACE DEBUG] Distance (miles): {distance_miles}, Moving time (sec): {moving_time}, Elapsed time (sec): {elapsed_time}")
    if distance_miles and distance_miles > 0:
        pace_sec = moving_time / distance_miles
        minutes = int(pace_sec // 60)
        seconds = int(pace_sec % 60)
        print(f"[PACE DEBUG] Calculated pace: {minutes}:{seconds:02d} min/mi (using moving_time)")
        return f"{minutes}:{seconds:02d} min/mi"
    return None

def seconds_per_km(activity):
    distance_km = activity.get("distance", 0) / 1000.0
    moving_time = activity.get("moving_time", 0)
    if distance_km > 0:
        pace_sec = moving_time / distance_km
        minutes = int(pace_sec // 60)
        seconds = int(pace_sec % 60)
        return f"{minutes}:{seconds:02d} min/km"
    return None

# TODO 
# - average pace and average HR do not match Garmin
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

def build_fulcrum_payload(activity, geojson):
    # Update these keys to match your Fulcrum Data Names exactly (Imperial units and correct conversions)
    form_values = {
        "7980": activity.get("name"),
        "2d48": activity.get("start_date_local", "")[:10],
        "3200": activity.get("type"),
        "9000": meters_to_miles(activity.get("distance")),
        "b890": round_or_none(activity.get("calories")),
        "1acf": seconds_per_mile(activity),  # min/mile
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
        "8f50": None, #min temp
        "5270": None, #max temp
        "446e": None, #aerobic TE
    }
    # Convert all non-None values to strings (Fulcrum expects string values)
    form_values = {k: str(v) for k, v in form_values.items() if v is not None}
    return {
        "record": {
            "geometry": geojson,
            "form_values": form_values
        }
    }

def read_fulcrum_token():
    return os.environ.get("FULCRUM_API_TOKEN")

def create_fulcrum_record(payload, form_id):
    api_token = read_fulcrum_token()
    url = "https://api.fulcrumapp.com/api/v2/records.json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-ApiToken": api_token
    }
    payload['record']['form_id'] = form_id

    # Debug: Print the exact payload and the field names
    print("\n==== Fulcrum Payload ====")
    print(json.dumps(payload, indent=2))
    print("Form Values Keys:", list(payload['record']['form_values'].keys()))

    resp = requests.post(url, headers=headers, json=payload)
    print("Fulcrum response:", resp.status_code)
    try:
        resp_json = resp.json()
        print(json.dumps(resp_json, indent=2))
        # Debug: Print errors if present
        if 'record' in resp_json and 'errors' in resp_json['record']:
            print("Fulcrum API Errors:", resp_json['record']['errors'])
    except Exception as e:
        print("Error parsing Fulcrum response as JSON:", e)
        print(resp.text)
    if resp.status_code != 201:
        print("Error creating Fulcrum record!")
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
            access_token = get_valid_access_token()
            activity = fetch_activity(activity_id, access_token)
            if activity:
                geojson = get_geojson_linestring(activity)
                payload = build_fulcrum_payload(activity, geojson)
                print("Payload for Fulcrum:")
                print(json.dumps(payload, indent=2))
                create_fulcrum_record(payload, FULCRUM_FORM_ID)
        return '', 200

if __name__ == '__main__':
    app.run(port=5055)
