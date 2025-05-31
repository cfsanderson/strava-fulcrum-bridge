#!/bin/bash
# Quickstart script for Strava → Fulcrum Webhook Bridge
# Usage: ./quickstart.sh

set -e

# 1. Install dependencies
if [ -f requirements.txt ]; then
    echo "Installing Python dependencies..."
    python -m pip install -r requirements.txt
else
    echo "requirements.txt not found!"
    exit 1
fi

# 2. Copy .env.example if .env does not exist
if [ ! -f .env ]; then
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "Please edit .env and fill in your real credentials before proceeding."
    exit 0
fi

# 3. Export environment variables from .env
export $(grep -v '^#' .env | xargs)

# 4. Run basic tests
if [ -f test_basic.py ]; then
    echo "Running basic tests..."
    if command -v pytest &> /dev/null; then
        pytest test_basic.py
    else
        python -m pytest test_basic.py || python test_basic.py
    fi
else
    echo "No test_basic.py found, skipping tests."
fi

# 5. Register Strava webhook if strava-auth.sh exists and is executable
if [ -x strava-auth.sh ]; then
    echo "Registering Strava webhook using strava-auth.sh..."
    ./strava-auth.sh
else
    echo "strava-auth.sh not found or not executable, skipping webhook registration."
fi

# 6. Start the app with Gunicorn
if [ -f Procfile ]; then
    echo "Starting app with Gunicorn..."
    gunicorn strava_webhook:app
else
    echo "Procfile not found! Starting app with Flask (dev mode)..."
    python strava_webhook.py
fi
