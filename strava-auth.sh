# after starting flask server and ngrok, copy the new ngrock url and run this
# Usage:
#   export STRAVA_CLIENT_ID=your_client_id
#   export STRAVA_CLIENT_SECRET=your_client_secret
#   export CALLBACK_URL=https://your-app-url/strava-webhook
#   ./strava-auth.sh

curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id="$STRAVA_CLIENT_ID" \
  -F client_secret="$STRAVA_CLIENT_SECRET" \
  -F callback_url="$CALLBACK_URL" \
  -F verify_token=anyToken