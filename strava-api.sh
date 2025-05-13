curl -X POST "https://<ngrok_url>.ngrok-free.app/strava-webhook" \
  -H "Content-Type: application/json" \
  -d '{"object_type":"activity","aspect_type":"create","object_id":<activity_id>}'

