# Training Calendar - Quick Reference

## Installation (One-Time)

```bash
# Install the service
sudo cp training-calendar.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable training-calendar.service
sudo systemctl start training-calendar.service
```

## Calendar Subscription URLs

**Local Network:**
- `http://YOUR_PI_IP:8080/training_calendar.ics` (replace with your Pi's actual IP)
- `http://raspberrypi.local:8080/training_calendar.ics`

**Subscribe in Apple Calendar:**
- Mac: File → New Calendar Subscription → Paste URL → Set refresh to "Every hour"
- iPhone: Settings → [Name] → iCloud → Calendar → Add Subscription

## Service Management

```bash
# Start/stop/restart
sudo systemctl start training-calendar.service
sudo systemctl stop training-calendar.service
sudo systemctl restart training-calendar.service

# Check status
sudo systemctl status training-calendar.service

# View logs
sudo journalctl -u training-calendar.service -f
```

## Manual Operations

```bash
# Regenerate calendar
source venv/bin/activate && python3 training_calendar/generator.py

# View planned workouts
sqlite3 training_calendar/training_plan.db "SELECT date, workout_type, distance_miles FROM planned_workouts LIMIT 10;"

# View completed activities
sqlite3 training_calendar/training_plan.db "SELECT date, activity_type, distance_miles, avg_pace FROM completed_activities;"

# Import new training plan
python3 training_calendar/import_plan.py new_plan.csv
```

## How Syncing Works

1. Hourly cron runs `stravasync 1`
2. Fetches latest Strava activity
3. Syncs to Fulcrum
4. Syncs to calendar database
5. Matches with planned workout
6. Regenerates .ics file
7. Your devices refresh and show updates

## Event Types

- 🏃 **Planned run** - Not yet completed
- 💪 **Planned strength** - Not yet completed
- ✅ **Completed** - Synced from Strava, matched to plan
- ⭐ **Extra Credit** - Completed but not in plan
- 🛌 **Rest Day** - All-day event

## Troubleshooting

**Calendar not updating?**
```bash
# Check service
sudo systemctl status training-calendar.service

# Test URL
curl http://localhost:8080/training_calendar.ics | head -20

# Force refresh on Mac: Right-click calendar → Refresh
```

**Activities not syncing?**
```bash
# Check sync logs
tail -f ~/Projects/strava-fulcrum-bridge/sync_cron.log

# Manual sync test
stravasync 1
```

**Port 8080 in use?**
```bash
# Check what's using it
sudo netstat -tuln | grep 8080

# Change port in run_calendar_server.sh if needed
```

## Files & Locations

- **Database:** `training_calendar/training_plan.db`
- **Calendar File:** `training_calendar/training_calendar.ics`
- **Service:** `/etc/systemd/system/training-calendar.service`
- **Wrapper:** `run_calendar_server.sh`
- **Logs:** `sudo journalctl -u training-calendar.service`

## Support

See full documentation: `CALENDAR_SETUP.md`
