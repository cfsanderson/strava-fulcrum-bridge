# Calendar Editing Guide

Quick reference for editing training calendar metadata.

## Edit Individual Workouts

### Update Notes
```bash
cd ~/Projects/strava-fulcrum-bridge
source venv/bin/activate

# Add or update notes for a workout
./edit_calendar.py update-note 2026-01-13 "Felt great today! Negative splits."

# Update multiple times (will overwrite previous note)
./edit_calendar.py update-note 2026-01-13 "Updated: Ran with Sarah"
```

### Update Title/Details
```bash
# Change the workout description
./edit_calendar.py update-title 2026-01-15 "Extended Easy Run"

# Example: Make it more descriptive
./edit_calendar.py update-title 2026-01-20 "Tempo Run - Marathon Pace"
```

### List Upcoming Workouts
```bash
# Show next 7 days (default)
./edit_calendar.py list

# Show next 14 days
./edit_calendar.py list 14

# Show workouts starting from specific date
./edit_calendar.py list 7 --start 2026-01-20
```

## Re-import Training Plan CSV

If you want to edit the entire plan (add/remove workouts, change dates, etc.):

1. **Edit your CSV file** (e.g., `training_plan.csv`)
   - Update any planned workouts
   - Add new weeks
   - Remove workouts
   - Change dates, distances, etc.

2. **Re-import the updated CSV**:
   ```bash
   cd ~/Projects/strava-fulcrum-bridge
   source venv/bin/activate

   ./reimport_plan.py training_plan.csv
   ```

3. **What happens**:
   - ✓ Database is backed up automatically
   - ✓ Planned workouts are replaced with CSV data
   - ✓ Completed activities are preserved
   - ✓ Completed activities are re-matched to new plan
   - ✓ Calendar is regenerated

## Important Notes

### What Gets Preserved During Re-import
- ✓ All completed activity data (from Strava syncs)
- ✓ Activity stats (pace, HR, elevation, etc.)
- ✓ Strava URLs
- ✓ Matches are re-created by date + activity type

### What Gets Overwritten During Re-import
- ✗ Planned workout details (replaced from CSV)
- ✗ Notes in planned workouts (unless in CSV)
- ✗ Distances/durations (replaced from CSV)

### Calendar Updates
After any edit, the `.ics` file is regenerated automatically. Subscribed calendars will refresh:
- iPhone: Every hour or when you open the Calendar app
- Mac Calendar: Every 15-60 minutes
- Google Calendar: Every 8-24 hours (varies)

## Workflow Examples

### Scenario 1: Fix a Typo in Today's Workout
```bash
# SSH into Pi
ssh pi@YOUR_PI_IP

# Navigate and activate venv
cd ~/Projects/strava-fulcrum-bridge
source venv/bin/activate

# Fix the typo
./edit_calendar.py update-title 2026-01-14 "Burn Bootcamp - Upper Body"

# Calendar updates automatically
# Your subscribed devices will see the change within an hour
```

### Scenario 2: Add Note After Completing Run
```bash
# After your run syncs from Strava
./edit_calendar.py update-note 2026-01-13 "PR! Felt strong throughout. Trail was muddy but fun."

# Note appears in calendar event description
```

### Scenario 3: Bulk Update Plan
```bash
# 1. Copy current CSV to your computer
scp pi@YOUR_PI_IP:~/Projects/strava-fulcrum-bridge/training_plan.csv .

# 2. Edit in Excel/Numbers/LibreOffice
# - Change Week 4 distances
# - Add rest day on Friday
# - Update notes column

# 3. Copy back to Pi
scp training_plan.csv pi@YOUR_PI_IP:~/Projects/strava-fulcrum-bridge/

# 4. SSH in and re-import
ssh pi@YOUR_PI_IP
cd ~/Projects/strava-fulcrum-bridge
source venv/bin/activate
./reimport_plan.py training_plan.csv

# Done! All your completed activities are still there.
```

## Troubleshooting

### "No planned workout found for [date]"
- Check the date format: Must be `YYYY-MM-DD`
- Verify workout exists: `./edit_calendar.py list 30`
- Check database: `sqlite3 training_calendar/training_plan.db "SELECT date FROM planned_workouts;"`

### Changes Not Showing on Calendar
- Calendar apps cache data (1-24 hours depending on app)
- Force refresh on iPhone: Settings → Calendar → Accounts → Refetch
- Check file was regenerated: `ls -lh training_calendar/training_calendar.ics`
- Test URL: `curl http://YOUR_PI_IP:8080/training_calendar.ics | grep "SUMMARY"`

### Re-import Went Wrong
If something breaks during re-import, restore from backup:
```bash
# Backups are created automatically: training_plan.db.backup.YYYYMMDD_HHMMSS
cd ~/Projects/strava-fulcrum-bridge
ls -lht training_calendar/*.backup* | head -1  # Find latest backup
cp training_calendar/training_plan.db.backup.20260114_150000 training_calendar/training_plan.db
python3 training_calendar/generator.py  # Regenerate calendar
```

## Quick Commands Reference

```bash
# List workouts
./edit_calendar.py list [days]

# Update note
./edit_calendar.py update-note YYYY-MM-DD "Note text"

# Update title
./edit_calendar.py update-title YYYY-MM-DD "Title text"

# Re-import CSV
./reimport_plan.py training_plan.csv

# View database
sqlite3 training_calendar/training_plan.db "SELECT * FROM planned_workouts WHERE date >= date('now') LIMIT 5;"

# Manual calendar regeneration (if needed)
python3 training_calendar/generator.py

# Check calendar server
sudo systemctl status training-calendar.service
curl http://localhost:8080/training_calendar.ics | head -20
```

## Pro Tips

1. **Bash Aliases**: Add to `~/.bash_aliases`:
   ```bash
   alias caledit='cd ~/Projects/strava-fulcrum-bridge && source venv/bin/activate && python3 edit_calendar.py'
   alias callist='cd ~/Projects/strava-fulcrum-bridge && source venv/bin/activate && python3 edit_calendar.py list'
   ```
   Then use: `caledit update-note 2026-01-14 "Great run!"`

2. **Batch Edits**: If you need to update many workouts, edit the CSV and re-import. It's faster than individual edits.

3. **Backup Before Big Changes**: Before major CSV re-imports:
   ```bash
   cp training_calendar/training_plan.db training_calendar/training_plan.db.manual_backup
   ```

4. **Check Logs**: If automatic syncs aren't updating the calendar:
   ```bash
   tail -f ~/Projects/strava-fulcrum-bridge/sync_cron.log
   ```
