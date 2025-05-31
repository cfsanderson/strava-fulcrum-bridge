#!/bin/bash

# Source environment variables from .env file in the current directory
if [ -f .env ]; then
  echo "Loading environment variables from .env file..."
  export $(grep -v '^#' .env | xargs)
else
  echo "Warning: .env file not found. Make sure environment variables are set."
fi

# Define the callback URL for the webhook *events*
# This should be the public URL for your /strava-webhook endpoint
WEBHOOK_EVENT_CALLBACK_URL="http://strava-fulcrum-bridge.duckdns.org:8000/strava-webhook"

# The verify token used here MUST match STRAVA_VERIFY_TOKEN in your .env file
# (which is loaded above)

echo "Attempting to register webhook with:"
echo "  Client ID: $STRAVA_CLIENT_ID"
echo "  Callback URL: $WEBHOOK_EVENT_CALLBACK_URL"
echo "  Verify Token: $STRAVA_VERIFY_TOKEN"
echo ""

curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id="$STRAVA_CLIENT_ID" \
  -F client_secret="$STRAVA_CLIENT_SECRET" \
  -F callback_url="$WEBHOOK_EVENT_CALLBACK_URL" \
  -F verify_token="$STRAVA_VERIFY_TOKEN"

