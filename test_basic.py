# test_basic.py
# Minimal test to check that the Flask app loads and the /strava-webhook endpoint is available.

from strava_webhook import app

def test_webhook_get():
    client = app.test_client()
    resp = client.get('/strava-webhook?hub.challenge=test')
    assert resp.status_code == 200
    assert 'hub.challenge' in resp.json

def test_webhook_post():
    client = app.test_client()
    sample_event = {
        "object_type": "activity",
        "aspect_type": "create",
        "object_id": 1234567890,
        "owner_id": 1,
        "subscription_id": 1,
        "updates": {}
    }
    resp = client.post('/strava-webhook', json=sample_event)
    assert resp.status_code == 200
