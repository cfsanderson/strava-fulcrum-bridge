# Training Calendar Setup Guide

## Overview

Your training calendar integration is now installed! This system:
- ✅ Stores your training plan in a SQLite database
- ✅ Automatically syncs Strava activities to the calendar
- ✅ Matches completed activities with planned workouts
- ✅ Tracks "extra credit" workouts not in the plan
- ✅ Serves a subscribable .ics calendar file via HTTP

## Quick Start

### 1. Install the Calendar Server Service

```bash
# Copy the service file to systemd
sudo cp training-calendar.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable training-calendar.service

# Start the service
sudo systemctl start training-calendar.service

# Check status
sudo systemctl status training-calendar.service
```

### 2. Verify the Calendar Server is Running

```bash
# Check if the server is accessible
curl http://localhost:8080/training_calendar.ics | head -20

# You should see iCalendar data starting with:
# BEGIN:VCALENDAR
# VERSION:2.0
# ...
```

### 3. Subscribe to the Calendar

#### On iPhone/iPad:

1. Open the **Settings** app
2. Tap your name at the top
3. Tap **iCloud**
4. Tap **Calendar**
5. Scroll down and tap **Subscribed Calendars**
6. Tap **Add Subscription**
7. Enter: `http://YOUR_PI_IP:8080/training_calendar.ics`
   - Replace `YOUR_PI_IP` with your Pi's IP address (e.g., `192.168.1.100`)
   - Or use: `http://raspberrypi.local:8080/training_calendar.ics`
8. Tap **Subscribe**
9. Set refresh frequency to **Every hour** or **Every day**
10. Choose a color and tap **Done**

#### On Mac:

1. Open **Calendar** app
2. Go to **File → New Calendar Subscription** (or press ⌘⌥S)
3. Enter: `http://YOUR_PI_IP:8080/training_calendar.ics`
   - Replace `YOUR_PI_IP` with your Pi's IP address
   - Or use: `http://raspberrypi.local:8080/training_calendar.ics`
4. Click **Subscribe**
5. Set:
   - **Auto-refresh**: Every hour or Every day
   - **Location**: Choose which calendar account to use
6. Click **OK**

## How It Works

### Automatic Sync

Every time your hourly cron job runs (`stravasync 1`), it:
1. Fetches the most recent Strava activity
2. Syncs it to Fulcrum (if not already there)
3. Syncs it to the training calendar database
4. Matches it with a planned workout (if same date and type)
5. Regenerates the .ics calendar file
6. Your devices will pick up the updates on their next refresh

### Calendar Events

- **Planned workouts**: Show with 🏃 (runs) or 💪 (strength) emoji
- **Completed workouts**: Show with ✅ emoji and actual stats (pace, HR, elevation)
- **Extra workouts**: Show with ⭐ emoji (unplanned activities)
- **Rest days**: Show as all-day events with 🛌 emoji

### Event Details

Completed events include:
- Actual distance and duration
- Pace (min/mile)
- Average and max heart rate
- Elevation gain
- Link to Strava activity
- Original workout notes

## Service Management

### Check Server Status

```bash
sudo systemctl status training-calendar.service
```

### View Server Logs

```bash
# View recent logs
sudo journalctl -u training-calendar.service -n 50

# Follow logs in real-time
sudo journalctl -u training-calendar.service -f

# View logs since a specific time
sudo journalctl -u training-calendar.service --since '1 hour ago'
```

### Restart the Service

```bash
sudo systemctl restart training-calendar.service
```

### Stop the Service

```bash
sudo systemctl stop training-calendar.service
```

## Manual Operations

### Manually Regenerate Calendar

```bash
cd ~/Projects/strava-fulcrum-bridge
source venv/bin/activate
python3 training_calendar/generator.py
```

### View Database Contents

```bash
# View planned workouts
sqlite3 training_calendar/training_plan.db "SELECT date, workout_type, distance_miles, notes FROM planned_workouts ORDER BY date LIMIT 10;"

# View completed activities
sqlite3 training_calendar/training_plan.db "SELECT date, activity_type, distance_miles, avg_pace FROM completed_activities ORDER BY date;"

# Check matched activities
sqlite3 training_calendar/training_plan.db "SELECT COUNT(*) as matched FROM completed_activities WHERE planned_workout_id IS NOT NULL;"

# Check unmatched activities (extra credit)
sqlite3 training_calendar/training_plan.db "SELECT date, activity_type, distance_miles FROM completed_activities WHERE planned_workout_id IS NULL;"
```

### Import a New Training Plan

```bash
cd ~/Projects/strava-fulcrum-bridge
source venv/bin/activate
python3 training_calendar/import_plan.py path/to/new_plan.csv
python3 training_calendar/generator.py
```

## Troubleshooting

### Calendar not updating on devices

1. Check that the service is running:
   ```bash
   sudo systemctl status training-calendar.service
   ```

2. Test the URL in your browser:
   ```
   http://YOUR_PI_IP:8080/training_calendar.ics
   ```

3. Force refresh in Apple Calendar:
   - Mac: Right-click the calendar → **Refresh**
   - iPhone/iPad: Settings → [Your Name] → iCloud → Calendar → Subscribed Calendars → Tap your calendar → Delete and re-add

### Activities not matching with planned workouts

Check the database to see what's not matching:

```bash
sqlite3 training_calendar/training_plan.db "SELECT ca.date, ca.activity_type, pw.workout_type, ca.planned_workout_id FROM completed_activities ca LEFT JOIN planned_workouts pw ON ca.date = pw.date WHERE ca.planned_workout_id IS NULL;"
```

Common reasons:
- Date mismatch (check start_date_local vs planned date)
- Activity type doesn't match (e.g., "WeightTraining" should match "Burn Bootcamp")
- No planned workout for that date

### Server won't start

Check port 8080 is available:

```bash
sudo netstat -tuln | grep 8080
```

If port is in use, you can change it:
1. Edit `run_calendar_server.sh`
2. Change `8080` to a different port (e.g., `8081`)
3. Restart the service: `sudo systemctl restart training-calendar.service`
4. Update your calendar subscription URL with the new port

### Strava activities not syncing to calendar

1. Check that the hourly sync is running:
   ```bash
   tail -20 ~/Projects/strava-fulcrum-bridge/sync_cron.log
   ```

2. Manually sync an activity to test:
   ```bash
   cd ~/Projects/strava-fulcrum-bridge
   source venv/bin/activate
   stravasync 1
   ```

3. Check if calendar sync is happening:
   ```bash
   # Should see "✓ Synced activity" messages in the output
   ```

## Network Access

### Local Network Only (Current Setup)

Your calendar is accessible on your local network at:
- `http://192.168.1.X:8080/training_calendar.ics` (your Pi's IP)
- `http://raspberrypi.local:8080/training_calendar.ics` (mDNS)

This works when your devices are on the same network as your Pi.

### Remote Access (Optional)

If you want to access your calendar from outside your home network:

**Option 1: Tailscale (Recommended)**
- Install Tailscale on your Pi and devices
- Access via Tailscale IP address
- Secure and easy: https://tailscale.com/

**Option 2: DuckDNS + Port Forwarding**
- Forward port 8080 on your router (like you did for port 8000)
- Update DuckDNS configuration
- Access via `http://your-domain.duckdns.org:8080/training_calendar.ics`

## File Structure

```
strava-fulcrum-bridge/
├── training_calendar/
│   ├── __init__.py                    # Package initialization
│   ├── import_plan.py                 # CSV import script
│   ├── generator.py                   # Calendar generation
│   ├── activity_sync.py               # Strava sync integration
│   ├── server.py                      # HTTP server
│   ├── training_plan.db               # SQLite database
│   └── training_calendar.ics          # Generated calendar file
├── run_calendar_server.sh             # Service wrapper script
├── training-calendar.service          # Systemd service file
├── phase1_training_plan.csv           # Your training plan CSV
└── CALENDAR_SETUP.md                  # This file
```

## Next Steps

1. ✅ Install and start the systemd service
2. ✅ Subscribe to the calendar on your devices
3. ✅ Wait for the next hourly sync (or run `stravasync 1` manually)
4. ✅ Check your calendar app - you should see your training plan!
5. ✅ Complete a workout and watch it automatically appear as completed

## Support

If you encounter issues:

1. Check service logs: `sudo journalctl -u training-calendar.service -f`
2. Check sync logs: `tail -f ~/Projects/strava-fulcrum-bridge/sync_cron.log`
3. Test URL: `curl http://localhost:8080/training_calendar.ics`
4. Verify database: `sqlite3 training_calendar/training_plan.db "SELECT COUNT(*) FROM planned_workouts;"`

---

**Enjoy your automated training calendar!** 🏃💪📅
