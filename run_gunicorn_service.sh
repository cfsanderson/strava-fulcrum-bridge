#!/bin/bash
# Wrapper script to run Gunicorn for the Strava Fulcrum Bridge service

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to the project directory
cd "$SCRIPT_DIR"

# Source environment variables from .env file
if [ -f .env ]; then
  echo "[$(date)] Sourcing .env file for strava-bridge service" >> /tmp/strava-bridge-service.log # Log that we are sourcing
  export $(grep -v '^#' .env | xargs)
else
  echo "[$(date)] ERROR: .env file not found for strava-bridge service" >> /tmp/strava-bridge-service.log
  exit 1 # Exit if .env is missing
fi

# Log the PORT variable to check
echo "[$(date)] PORT variable is: $PORT" >> /tmp/strava-bridge-service.log

# Check if PORT is empty or not a number
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "[$(date)] ERROR: PORT variable is not a valid number or is empty. Value: '$PORT'" >> /tmp/strava-bridge-service.log
    exit 1
fi

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Execute Gunicorn - use exec so Gunicorn replaces this script process
# This allows systemd to correctly manage the Gunicorn process directly
echo "[$(date)] Starting Gunicorn with PORT: $PORT (DUAL FORM MODE)" >> /tmp/strava-bridge-service.log
exec "$SCRIPT_DIR/venv/bin/gunicorn" strava_webhook_dual_form:app --bind 0.0.0.0:$PORT

