#!/bin/bash
# Wrapper script for syncing Strava activities to Fulcrum
# Usage: strava_sync.sh [number_of_activities]

SCRIPT_DIR="$HOME/Projects/strava-fulcrum-bridge"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"
SYNC_SCRIPT="$SCRIPT_DIR/sync_activities.py"
LOG_FILE="$SCRIPT_DIR/sync_cron.log"

# Default to syncing 1 activity if no argument provided
COUNT=${1:-1}

# Validate the count is a number
if ! [[ "$COUNT" =~ ^[0-9]+$ ]]; then
    echo "Error: Please provide a valid number of activities to sync"
    echo "Usage: strava_sync.sh [number]"
    echo "Example: strava_sync.sh 5"
    exit 1
fi

cd "$SCRIPT_DIR" || exit 1

# Run the sync script
"$VENV_PYTHON" "$SYNC_SCRIPT" "$COUNT" --days 30

