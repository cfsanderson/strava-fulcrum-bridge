# Strava-to-Fulcrum Bridge on Raspberry Pi

This guide details how to set up and run an "always-on" server on a Raspberry Pi. This setup uses DuckDNS for dynamic IP handling, port forwarding, and `systemd` for robust service management.

The primary goal is to have a personal server that listens for Strava webhook events (new activities) and then pushes processed data to a specified Fulcrumapp.com form. The main use case was to capture data from running activities so the script also transforms the Garmin/Strava GPX data into usable GEOJSON for Fulcrum. Any Strava activity will be synced (e.g. strength training, yoga, cycling, etc.) but the Fulcrum form should be built to receive the inputs.

## Prerequisites

### Hardware
*   A Raspberry Pi (Raspberry Pi 3B+ or newer recommended. This guide was tested with a Pi 3B).
*   A reliable microSD card (16GB+).
*   A stable power supply for the Raspberry Pi (e.g., 5V 2.5A for Pi 3B).
*   Ethernet connection to your router (recommended for server stability) or stable Wi-Fi.
*   A computer (e.g., Macbook Pro) for initial setup and SSH access.

### Software & Accounts
*   **Raspberry Pi OS Lite:** (32-bit recommended for Pi 3B, 64-bit for Pi 4/400).
*   **Strava Account:** With API application created.
*   **Fulcrumapp.com Account:** With an API token and a Form ID for data submission.
*   **DuckDNS Account:** (Or another Dynamic DNS provider).
*   **Git:** Installed on your Raspberry Pi.
*   Basic familiarity with Linux command line and SSH.

## Setup Instructions

### Phase 1: Raspberry Pi Initial Setup

1.  **Install Raspberry Pi OS Lite:**
    *   Use Raspberry Pi Imager to flash Raspberry Pi OS Lite (e.g., 32-bit for Pi 3B) to your microSD card.
    *   **Headless Setup via Imager:** Before writing, use the "Advanced Options" (gear icon) in Raspberry Pi Imager to:
        *   Enable SSH (set a username and password, or preferably configure public-key authentication). This guide assumes username `your-name`.
        *   Configure Wi-Fi if you plan to use it initially (Ethernet is preferred for the server).
        *   Set your hostname (e.g., `strava-bridge`).
        *   Set locale and keyboard layout.

2.  **First Boot and SSH:**
    *   Insert the SD card into your Pi and boot it up.
    *   Find your Pi's IP address on your local network (e.g., via your router's DHCP client list).
    *   SSH into your Pi: `ssh your-name@YOUR_PI_IP_ADDRESS`

3.  **Set a Static IP Address (DHCP Reservation):**
    *   Log in to your router.
    *   Find your Pi's MAC address (`ip link show eth0` on the Pi).
    *   Configure DHCP reservation on your router to assign a permanent local IP address to your Pi (e.g., `192.168.1.192`). Reboot the Pi and verify it gets the static IP.

4.  **System Update:**
    ```bash
    sudo apt update && sudo apt full-upgrade -y
    ```

### Phase 2: Network Configuration for Public Access

1.  **Dynamic DNS (DDNS) with DuckDNS:**
    *   Go to `https://www.duckdns.org/` and sign in.
    *   Create a subdomain (e.g., `your-strava-bridge.duckdns.org`). Note your token.
    *   Set up a cron job on your Pi to update DuckDNS automatically:
        ```bash
        sudo crontab -e
        ```
        Add the following line (replace with your domain and token):
        ```cron
        */5 * * * * curl -k -s "https://www.duckdns.org/update?domains=your-strava-bridge&token=YOUR_DUCKDNS_TOKEN&ip=" >/dev/null 2>&1
        ```
        Save and exit. Verify by manually running the `curl` command (it should output "OK").

2.  **Port Forwarding:**
    *   Log in to your router.
    *   Set up a port forwarding rule to forward an external TCP port (e.g., `8000`) to your Pi's static internal IP address (e.g., `192.168.1.192`) on port `8000` (the port Gunicorn will listen on).
    *   Example rule settings:
        *   Application: `strava-bridge`
        *   Original Port (External): `8000`
        *   Protocol: `TCP`
        *   Forward to Address (Internal IP): `192.168.1.192`
        *   Forward to Port (Internal): `8000`
        *   Schedule: `Always`

### Phase 3: Security (Firewall - UFW)

1.  **Install UFW:**
    ```bash
    sudo apt install ufw -y
    ```
2.  **Set Default Policies & Allow Ports:**
    ```bash
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh  # Or your custom SSH port
    sudo ufw allow 8000/tcp # Port for the Strava bridge application
    sudo ufw enable     # Confirm with 'y'
    sudo ufw status verbose
    ```

### Phase 4: Application Environment Setup

1.  **Install Git:**
    ```bash
    sudo apt install git -y
    ```
2.  **Clone the Project Repository:**
    ```bash
    cd ~ # Or your preferred projects directory
    mkdir -p Projects && cd Projects 
    git clone https://github.com/YOUR_USERyour-name/strava-fulcrum-bridge.git # Or the original repo URL
    cd strava-fulcrum-bridge
    ```
3.  **Set up Python Virtual Environment:**
    ```bash
    sudo apt install python3-venv -y
    python3 -m venv venv
    source venv/bin/activate 
    # Your prompt should now show (venv)
    ```
4.  **Install Python Dependencies:**
    ```bash
    (venv) pip install -r requirements.txt
    ```

### Phase 5: Project Configuration

1.  **Create `.env` File:**
    ```bash
    (venv) cp .env.example .env
    (venv) nano .env
    ```
    Populate with your actual credentials:
    ```env
    STRAVA_CLIENT_ID=YOUR_STRAVA_CLIENT_ID
    STRAVA_CLIENT_SECRET=YOUR_STRAVA_CLIENT_SECRET
    STRAVA_REFRESH_TOKEN= # Leave blank initially, will be populated by OAuth flow
    STRAVA_VERIFY_TOKEN=CHOOSE_A_STRONG_RANDOM_STRING # e.g., generate with `openssl rand -hex 16`
    FULCRUM_API_TOKEN=YOUR_FULCRUM_API_TOKEN
    FULCRUM_FORM_ID=YOUR_FULCRUM_FORM_ID
    PORT=8000
    CALLBACK_URL=http://your-strava-bridge.duckdns.org:8000/exchange_token # For OAuth
    ```
    **Note:** The `STRAVA_REFRESH_TOKEN` will be stored in `.strava-tokens.json` by the app after the first successful OAuth flow.

2.  **Configure Strava API Application:**
    *   Go to `https://www.strava.com/settings/api`.
    *   Ensure your application is created.
    *   Set **"Authorization Callback Domain"** to your DuckDNS hostname (e.g., `your-strava-bridge.duckdns.org`). Do *not* include `http://` or port numbers here.

3.  **(Recommended) Modify `strava_webhook.py` for Robust Token Exchange:**
    In the `/exchange_token` function within `strava_webhook.py`, ensure the `redirect_uri` is included in the POST request to Strava's token endpoint:
    ```python
    # ... inside /exchange_token function ...
    token_exchange_redirect_uri = os.environ.get('CALLBACK_URL')
    if not token_exchange_redirect_uri:
        return "CALLBACK_URL not set in environment", 500
    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': token_exchange_redirect_uri # Ensure this line is present
        }
    )
    # ...
    ```

### Phase 6: Obtaining Initial Strava OAuth Tokens (First Run Only)

This step populates `.strava-tokens.json`.

1.  **Start the Application Manually (via `quickstart.sh`):**
    *   Ensure your `.env` file has the correct `CALLBACK_URL` (pointing to `/exchange_token`).
    *   In an SSH terminal on your Pi, with the `venv` active:
        ```bash
        (venv) ./quickstart.sh
        ```
    *   Gunicorn should start and listen on port 8000. Keep this terminal running.

2.  **Construct the Strava Authorization URL:**
    On your computer's browser, create and navigate to this URL (replace placeholders):
    `https://www.strava.com/oauth/authorize?client_id=YOUR_STRAVA_CLIENT_ID&redirect_uri=http://your-strava-bridge.duckdns.org:8000/exchange_token&response_type=code&approval_prompt=auto&scope=read_all,activity:read_all`

3.  **Authorize the Application:**
    *   Log in to Strava and click "Authorize."
    *   Your browser will be redirected to your `/exchange_token` endpoint.
    *   Check the Gunicorn logs for activity.
    *   A `.strava-tokens.json` file should be created in your project directory with your tokens. Verify its contents.

### Phase 7: Setting up the Strava Webhook Subscription

1.  **Stop Gunicorn (Ctrl+C in its terminal).**
2.  **Modify `strava-auth.sh`:**
    ```bash
    (venv) nano strava-auth.sh
    ```
    Ensure it looks similar to this (using variables from `.env`):
    ```bash
    #!/bin/bash
    if [ -f .env ]; then
      export $(grep -v '^#' .env | xargs)
    fi
    WEBHOOK_EVENT_CALLBACK_URL="http://your-strava-bridge.duckdns.org:8000/strava-webhook"
    echo "Attempting to register webhook with:"
    echo "  Client ID: $STRAVA_CLIENT_ID"
    echo "  Callback URL: $WEBHOOK_EVENT_CALLBACK_URL"
    echo "  Verify Token: $STRAVA_VERIFY_TOKEN"
    curl -X POST https://www.strava.com/api/v3/push_subscriptions \
      -F client_id="$STRAVA_CLIENT_ID" \
      -F client_secret="$STRAVA_CLIENT_SECRET" \
      -F callback_url="$WEBHOOK_EVENT_CALLBACK_URL" \
      -F verify_token="$STRAVA_VERIFY_TOKEN"
    ```
    Make it executable: `chmod +x strava-auth.sh`.

3.  **Restart Gunicorn:** `(venv) ./quickstart.sh` (keep it running).
4.  **Run `strava-auth.sh` to Subscribe:**
    In a *separate* SSH terminal (with `venv` active and `.env` variables potentially re-exported if needed: `export $(grep -v '^#' .env | xargs)`):
    ```bash
    (venv) ./strava-auth.sh
    ```
    *   A successful response will be a JSON object with a subscription ID (e.g., `{"id":12345}`).
    *   Check Gunicorn logs for the verification `GET` request from Strava to your `/strava-webhook` endpoint.

    *Troubleshooting Webhook Subscription:*
    *   If you get an "already exists" error, you may need to view and delete old subscriptions first using `curl` API calls (refer to Strava API docs or previous conversation steps for `GET` and `DELETE` on `/push_subscriptions`).

### Phase 8: Running as a `systemd` Service (for "Always On")

1.  **Stop any manually running Gunicorn instance (Ctrl+C).**
2.  **Create a Wrapper Script (`run_gunicorn_service.sh`):**
    In your project directory (`/home/your-name/Projects/strava-fulcrum-bridge/`):
    ```bash
    (venv) nano run_gunicorn_service.sh
    ```
    Paste the following (ensure paths and username `your-name` are correct):
    ```bash
    #!/bin/bash
    cd /home/your-name/Projects/strava-fulcrum-bridge
    if [ -f .env ]; then
      export $(grep -v '^#' .env | xargs)
    else
      exit 1 # Exit if .env is missing
    fi
    if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
        exit 1 # Exit if PORT is not a number
    fi
    source /home/your-name/Projects/strava-fulcrum-bridge/venv/bin/activate
    exec /home/your-name/Projects/strava-fulcrum-bridge/venv/bin/gunicorn strava_webhook:app --bind 0.0.0.0:$PORT
    ```
    Make it executable: `(venv) chmod +x run_gunicorn_service.sh`

3.  **Create the `systemd` Service File:**
    ```bash
    sudo nano /etc/systemd/system/strava-bridge.service
    ```
    Paste the following (ensure `User`, `Group`, and `ExecStart` paths are correct for `your-name`):
    ```ini
    [Unit]
    Description=Strava to Fulcrum Bridge Service
    After=network.target

    [Service]
    User=your-name
    Group=your-name
    ExecStart=/home/your-name/Projects/strava-fulcrum-bridge/run_gunicorn_service.sh
    Restart=always
    RestartSec=10
    KillSignal=SIGINT
    TimeoutStopSec=30
    SyslogIdentifier=strava-bridge

    [Install]
    WantedBy=multi-user.target
    ```

4.  **Reload, Enable, and Start the Service:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable strava-bridge.service
    sudo systemctl start strava-bridge.service
    ```

5.  **Check Service Status:**
    ```bash
    sudo systemctl status strava-bridge.service
    # Look for "Active: active (running)"
    # Press 'q' to exit status
    ```
    Check logs if needed: `sudo journalctl -u strava-bridge.service -f`

## Testing

1.  Record a new activity on Strava.
2.  Monitor the `systemd` service logs: `sudo journalctl -u strava-bridge.service -f`
3.  Check if the new activity data appears in your Fulcrumapp.com form.

## Notes
*   The `quickstart.sh` script attempts to run `pytest` and register webhooks. The `pytest` step may fail if `pytest` isn't installed (it's not in `requirements.txt`). The webhook registration in `quickstart.sh` might fail due to Gunicorn not being ready; rely on the manual `strava-auth.sh` execution for initial setup.
*   For true production use, consider setting up a reverse proxy (like Nginx or Caddy) to handle HTTPS/SSL for your DuckDNS endpoint.
*   Keep all your API tokens and secrets secure in the `.env` file and ensure `.env` is in your `.gitignore`.
