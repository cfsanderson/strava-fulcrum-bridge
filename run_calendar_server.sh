#!/bin/bash
# Wrapper script to run the training calendar server
# This script activates the virtual environment and starts the calendar HTTP server

# Navigate to the project directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Run the calendar server
exec python3 training_calendar/server.py 8080
