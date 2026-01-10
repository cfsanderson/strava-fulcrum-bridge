# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) and other developers when working with this project.

## Project Overview

**Strava-to-Fulcrum Bridge** is a Flask application that syncs Strava activities to Fulcrum forms. It runs as a systemd service on a Raspberry Pi and uses webhooks (with limitations) plus scheduled syncs to capture activity data.

**Primary Use Case**: Automatically sync running/cycling activities from Garmin watch → Garmin Connect → Strava → Fulcrum for personal fitness tracking and mapping.

## Architecture

### Components

1. **Flask Application** (`strava_webhook.py`)
   - `/exchange_token` - OAuth token exchange endpoint
   - `/strava-webhook` - Webhook receiver for Strava events (GET for verification, POST for events)
   - Automatic token refresh using `.strava-tokens.json`
   - Transforms Strava polylines to GeoJSON for Fulcrum
   - Converts metric values to imperial units for Fulcrum fields

2. **Manual Sync Script** (`sync_activities.py`)
   - CLI tool for manually syncing activities
   - Interactive mode with activity selection
   - Batch sync for recent activities
   - Uses shared functions from `strava_webhook.py`

3. **Wrapper Scripts**
   - `run_gunicorn_service.sh` - Systemd service wrapper (loads .env, starts Gunicorn)
   - `strava_sync.sh` - Manual sync wrapper for bash alias
   - `quickstart.sh` - Development testing script
   - `strava-auth.sh` - Webhook subscription registration

### Data Flow

```
Garmin Watch
    ↓
Garmin Connect (auto-sync)
    ↓
Strava (imported activity - NO webhook fired)
    ↓
Hourly Cron Job (fallback)
    ↓
Strava API (fetch activity details)
    ↓
Transform (polyline → GeoJSON, metric → imperial)
    ↓
Fulcrum API (create record)
```

## Critical Limitation: Garmin Connect and Webhooks

**⚠️ IMPORTANT**: Strava webhooks **do NOT fire** for activities synced from third-party apps like Garmin Connect.

### What Triggers Webhooks
- Activities created directly on Strava
- Manual uploads to Strava
- Activities created via Strava mobile app

### What Does NOT Trigger Webhooks
- Activities imported from Garmin Connect
- Activities synced from Garmin watches
- Any third-party activity imports

**This is a Strava API limitation, not a bug in this application.**

### Solution: Automatic Hourly Sync

A cron job runs every hour to sync the most recent activity:

```bash
# Crontab entry
0 * * * * cd /home/caleb/Projects/strava-fulcrum-bridge && /home/caleb/Projects/strava-fulcrum-bridge/venv/bin/python3 sync_activities.py 1 --days 1 >> /home/caleb/Projects/strava-fulcrum-bridge/sync_cron.log 2>&1
```

**Log file**: `sync_cron.log` in project directory

## Development Setup

### Prerequisites
- Python 3.11+
- Virtual environment
- Strava API application (client ID, client secret)
- Fulcrum API token and form ID
- DuckDNS domain (for production webhook)

### Initial Setup

```bash
# Clone and setup
cd ~/Projects
git clone <repository-url>
cd strava-fulcrum-bridge

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Fill in your credentials
```

### Environment Variables (.env)

```bash
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_VERIFY_TOKEN=random_string_for_webhook_verification
FULCRUM_API_TOKEN=your_fulcrum_token
FULCRUM_FORM_ID=your_form_id
PORT=8000
CALLBACK_URL=http://your-domain.duckdns.org:8000/exchange_token
```

**Note**: `STRAVA_REFRESH_TOKEN` is stored in `.strava-tokens.json` after OAuth flow, not in `.env`.

### OAuth Token Setup (First Time Only)

1. Start the application:
   ```bash
   source venv/bin/activate
   ./quickstart.sh
   ```

2. Navigate to the Strava authorization URL (replace with your client ID):
   ```
   https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://your-domain.duckdns.org:8000/exchange_token&response_type=code&approval_prompt=auto&scope=read_all,activity:read_all
   ```

3. Authorize the app - it will redirect to `/exchange_token` and create `.strava-tokens.json`

### Running Locally

```bash
# Development (Flask debug mode)
source venv/bin/activate
python3 strava_webhook.py

# Production-like (Gunicorn)
./quickstart.sh
```

## Common Tasks

### Manual Activity Sync

```bash
# Sync 1 most recent activity
stravasync 1

# Or directly with Python
source venv/bin/activate
python3 sync_activities.py 1

# Sync 5 most recent activities
python3 sync_activities.py 5

# Interactive mode (select specific activities)
python3 sync_activities.py -i

# Look back further (60 days)
python3 sync_activities.py -i --days 60
```

### Service Management (on Raspberry Pi)

```bash
# Check status
sudo systemctl status strava-bridge.service

# View logs
sudo journalctl -u strava-bridge.service -f
sudo journalctl -u strava-bridge.service --since '1 hour ago'

# Restart after code changes
sudo systemctl restart strava-bridge.service

# View sync cron logs
tail -f ~/Projects/strava-fulcrum-bridge/sync_cron.log
```

### Webhook Management

```bash
# View current webhook subscriptions
curl "https://www.strava.com/api/v3/push_subscriptions?client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"

# Register new webhook
./strava-auth.sh

# Delete webhook (replace SUBSCRIPTION_ID)
curl -X DELETE "https://www.strava.com/api/v3/push_subscriptions/SUBSCRIPTION_ID?client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

## Code Structure

### Key Functions in `strava_webhook.py`

- `exchange_token()` - OAuth token exchange endpoint
- `get_valid_access_token()` - Token refresh with retry logic and exponential backoff
- `read_strava_tokens()` / `write_strava_tokens()` - Token file management
- `fetch_activity(activity_id, access_token)` - Get full activity details from Strava
- `get_geojson_linestring(activity)` - Convert polyline to GeoJSON LineString
- `build_fulcrum_payload(activity, geojson)` - Transform Strava data to Fulcrum format
- `create_fulcrum_record(payload, form_id)` - Submit record to Fulcrum API
- `strava_webhook()` - Main webhook endpoint (GET/POST handler)

### Data Transformations

The application performs several conversions for Fulcrum:

- **Distance**: meters → miles (`meters_to_miles()`)
- **Elevation**: meters → feet (`meters_to_feet()`)
- **Temperature**: Celsius → Fahrenheit (`celsius_to_fahrenheit()`)
- **Pace**: seconds/meter → min/mile (`seconds_per_mile()`)
- **Time**: seconds → HH:MM:SS (`seconds_to_hms()`)
- **Polyline**: Strava encoded polyline → GeoJSON LineString

### Fulcrum Field Mapping

Field IDs in `build_fulcrum_payload()` map to specific Fulcrum form fields:

```python
"7980": activity.get("name"),              # Activity name
"2d48": activity.get("start_date_local"),  # Date
"3200": activity.get("type"),              # Activity type
"9000": meters_to_miles(distance),         # Distance (miles)
"b890": calories,                          # Calories
"1acf": seconds_per_mile(),                # Pace (min/mile)
"2050": average_heartrate,                 # Avg HR
"4c8d": max_heartrate,                     # Max HR
# ... etc
```

**Important**: If you modify the Fulcrum form, update these field IDs in the code.

## Testing

```bash
# Run basic tests
source venv/bin/activate
pytest test_basic.py

# Test webhook endpoint locally
curl http://localhost:8000/strava-webhook?hub.challenge=test123

# Test manual sync
python3 sync_activities.py 1
```

## Troubleshooting

### No Activities Syncing

1. **Check cron logs**: `tail -f ~/Projects/strava-fulcrum-bridge/sync_cron.log`
2. **Verify cron job**: `crontab -l`
3. **Check Strava tokens**: Ensure `.strava-tokens.json` exists and isn't expired
4. **Test manual sync**: `stravasync 1` to see error messages

### Token Refresh Failures

- Delete `.strava-tokens.json` and re-run OAuth flow
- Check `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` in `.env`
- Verify `CALLBACK_URL` matches Strava API settings

### Fulcrum API Errors

- Check `FULCRUM_API_TOKEN` is valid
- Verify `FULCRUM_FORM_ID` matches your form
- Review field IDs in `build_fulcrum_payload()` match your Fulcrum form schema
- Check Fulcrum API response in logs for detailed error messages

### Service Won't Start

```bash
# Check service status
sudo systemctl status strava-bridge.service

# View detailed logs
sudo journalctl -u strava-bridge.service -n 50

# Common issues:
# - .env file missing or malformed
# - PORT not set or invalid
# - Virtual environment missing dependencies
# - Permissions on run_gunicorn_service.sh
```

### Webhook Not Receiving Events

**Remember**: Webhooks don't fire for Garmin Connect imports. But if you're testing with direct Strava activities:

1. Check webhook subscription: See "Webhook Management" section above
2. Verify DuckDNS is updating: `curl -k -s "https://www.duckdns.org/update?domains=YOUR_DOMAIN&token=YOUR_TOKEN&ip="`
3. Test external connectivity: `curl http://your-domain.duckdns.org:8000/strava-webhook?hub.challenge=test`
4. Check router port forwarding (port 8000)
5. Verify UFW firewall allows port 8000: `sudo ufw status`

## Production Deployment (Raspberry Pi)

### System Requirements
- Raspberry Pi 3B+ or newer
- Raspberry Pi OS Lite (32-bit or 64-bit)
- Stable power supply (5V 2.5A minimum)
- Static IP address via DHCP reservation
- Port forwarding on router

### Deployment Steps

See `README.md` for complete production setup including:
- Network configuration (DuckDNS, port forwarding)
- Firewall setup (UFW)
- Systemd service configuration
- OAuth token setup
- Webhook registration

## Performance Considerations

### Resource Usage

- **Service**: ~50-100MB RAM, minimal CPU when idle
- **Cron job**: Runs for ~2-5 seconds per hour, very lightweight
- **Manual sync**: Scales with number of activities (network-bound)

### API Rate Limits

- **Strava API**: 100 requests per 15 minutes, 1000 requests per day (per application)
- **Fulcrum API**: Varies by plan (check your account limits)

The hourly cron job uses minimal API calls:
- 1 call to list recent activities
- 1 call per activity to fetch details (only for new activities)
- 1 call to Fulcrum per new activity

## Security Notes

- `.env` file contains secrets - never commit to Git (in `.gitignore`)
- `.strava-tokens.json` contains OAuth tokens - never commit to Git (in `.gitignore`)
- The service runs on HTTP, not HTTPS (consider adding reverse proxy with SSL for production)
- DuckDNS domain is public - ensure strong verification tokens

## Contributing

When making changes:

1. Test locally with `./quickstart.sh`
2. Test manual sync: `python3 sync_activities.py 1`
3. Update this `CLAUDE.md` if behavior changes
4. Update `README.md` for user-facing changes
5. Restart service on Pi after deployment: `sudo systemctl restart strava-bridge.service`

## Files Reference

### Application Files
- `strava_webhook.py` - Main Flask application
- `sync_activities.py` - Manual sync CLI tool
- `test_basic.py` - Basic tests

### Configuration Files
- `.env` - Environment variables (secrets, API keys)
- `.strava-tokens.json` - OAuth tokens (auto-generated, auto-refreshed)
- `requirements.txt` - Python dependencies

### Scripts
- `run_gunicorn_service.sh` - Systemd service wrapper
- `strava_sync.sh` - Manual sync wrapper (bash alias)
- `quickstart.sh` - Development testing script
- `strava-auth.sh` - Webhook registration helper
- `strava-api.sh` - API testing helper

### Documentation
- `README.md` - Complete setup guide
- `CLAUDE.md` - This file (development guide)
- `.env.example` - Example environment configuration
- `RUN Fulcrum App Builder.fulcrumapp` - Template Fulcrum form

### Logs
- `sync_cron.log` - Automatic hourly sync logs
- `strava-bridge.log` - Application logs (if logging to file)
- System logs: `sudo journalctl -u strava-bridge.service`

## Dependencies

From `requirements.txt`:
```
Flask
requests
polyline
python-dotenv
gunicorn
inquirer
```

Optional for development:
```
pytest  # For running tests
```

## Future Improvements

- [ ] Add duplicate detection to avoid re-syncing existing activities
- [ ] Implement HTTPS/SSL via reverse proxy (Nginx/Caddy)
- [ ] Add activity_id to Fulcrum records for better duplicate checking
- [ ] Create web UI for viewing sync status
- [ ] Add support for other activity sources beyond Garmin/Strava
- [ ] Implement proper logging with rotation
- [ ] Add Prometheus metrics for monitoring
- [ ] Support multiple Fulcrum forms (per activity type)

## Support & Resources

- Strava API Docs: https://developers.strava.com/docs/reference/
- Fulcrum API Docs: https://developer.fulcrumapp.com/
- DuckDNS: https://www.duckdns.org/
- Flask Documentation: https://flask.palletsprojects.com/
- Gunicorn Documentation: https://docs.gunicorn.org/

## Last Updated

January 10, 2026 - Added documentation for automatic sync workaround for Garmin Connect limitation
