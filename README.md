# Strava-to-Fulcrum Bridge on Raspberry Pi

This guide details how to set up and run an "always-on" server on a Raspberry Pi. This setup uses DuckDNS for dynamic IP handling, port forwarding, and `systemd` for robust service management.

The primary goal is to have a personal server that listens for Strava webhook events (new activities) and then pushes processed data to a specified Fulcrumapp.com form. The main use case is to capture data from running activities so the script also transforms the Garmin/Strava GPX data into usable GeoJSON for Fulcrum. Any Strava activity will be synced (e.g. strength training, yoga, cycling, etc.) but the Fulcrum form should be built to receive the inputs. The `run_fulcrum_app_builder.fulcrumapp` file is included as a template Fulcrum form.

**Important:** Your Fulcrum form must include a text field with data name `strava_activity_id` for duplicate detection to work properly. This field stores the unique Strava activity ID and prevents the same activity from being synced multiple times.

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

4.  **Configure Fulcrum Form:**
    *   In your Fulcrum form, ensure you have a **Text Field** with the data name `strava_activity_id`.
    *   This field is required for duplicate detection to work properly.
    *   To add this field:
        1. Go to your Fulcrum form builder
        2. Add a new "Text Field" (single line)
        3. Set the label to "Strava Activity ID" or similar
        4. The data name should automatically be set to `strava_activity_id`
        5. This field can be non-required since existing records won't have it
    *   The application will automatically populate this field with the Strava activity ID for each synced activity.
    *   Without this field, the duplicate detection will not work and activities may be synced multiple times.

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

---

## Manual Activity Sync

In addition to the automatic webhook-based sync, you can use the `sync_activities.py` script to manually sync activities from Strava to Fulcrum. This is useful for backfilling historical data or syncing specific activities.

### Prerequisites

1. Ensure you have the required Python package installed:
   ```bash
   source venv/bin/activate
   pip install inquirer
   ```

### Basic Usage

1. **Interactive Mode** (Recommended):
   ```bash
   python3 sync_activities.py -i
   ```
   - Shows an interactive menu of recent activities
   - Use arrow keys to navigate
   - Press space to select/deselect activities
   - Press enter to confirm selection
   - Type 'y' to confirm sync

2. **Sync Specific Number of Recent Activities**
   ```bash
   # Sync the 5 most recent activities
   python3 sync_activities.py 5
   ```

3. **Change the Lookback Period**
   ```bash
   # Show activities from the last 60 days
   python3 sync_activities.py -i --days 60
   ```

4. **Non-Interactive Mode**
   ```bash
   # Sync the 3 most recent activities from the last 30 days
   python3 sync_activities.py 3
   ```

### Features

- **Duplicate Prevention**: Automatically skips activities that already exist in Fulcrum by checking the `strava_activity_id` field
- **Detailed Logging**: See exactly what's happening during the sync process
- **Flexible Date Ranges**: Specify how far back to look for activities
- **Activity Selection**: Choose exactly which activities to sync
- **Smart Syncing**: Queries all existing Fulcrum records to ensure no duplicates are created

### Common Use Cases

1. **Backfilling Historical Data**:
   ```bash
   # Show activities from the last year
   python3 sync_activities.py -i --days 365
   ```

2. **Syncing a Specific Activity**:
   - Use interactive mode to select just the activity you want
   - Or use the non-interactive mode with a count of 1 for the most recent activity

3. **Regular Manual Syncs**:
   - Create a cron job to run the script periodically
   - Example (runs at 2 AM daily):
     ```
     0 2 * * * cd /path/to/strava-fulcrum-bridge && /path/to/venv/bin/python3 sync_activities.py 10
     ```

## Important Note: Garmin Connect and Webhook Limitations

**If you sync activities from Garmin Connect (or other third-party apps) to Strava, the webhook system will NOT trigger automatically.**

Strava's webhook events only fire for:
- Activities created directly on Strava
- Manual uploads to Strava
- Activities created via Strava's mobile app

**Activities imported from Garmin Connect, Garmin watches, or other third-party services bypass the webhook system by design.** This is a Strava API limitation, not a bug in this application.

### Solution: Automatic Hourly Sync

To work around this limitation, an automatic hourly sync has been configured using a cron job:

**Cron Job Configuration:**
```bash
# Syncs the most recent activity every hour
0 * * * * cd /home/pi/strava-fulcrum-bridge && /home/pi/strava-fulcrum-bridge/venv/bin/python3 sync_activities.py 1 --days 1 >> /home/pi/strava-fulcrum-bridge/sync_cron.log 2>&1
```

**What it does:**
- Runs every hour at the top of the hour (:00)
- Syncs the most recent activity from the last 24 hours
- Automatically skips activities that already exist in Fulcrum (duplicate detection)
- Logs all output to `sync_cron.log` in the project directory
- Very lightweight on system resources (just a few API calls)

**Monitoring the automatic sync:**
```bash
# View recent sync logs
tail -20 ~/Projects/strava-fulcrum-bridge/sync_cron.log

# Watch live sync activity
tail -f ~/Projects/strava-fulcrum-bridge/sync_cron.log

# Check when next sync will run
crontab -l
```

### Manual Sync Alias

For immediate syncing after a workout, a bash alias has been created for convenience:

**Usage:**
```bash
stravasync 1    # Sync 1 most recent activity
stravasync 5    # Sync 5 most recent activities
stravasync 10   # Sync 10 most recent activities
```

**Implementation:**
The `stravasync` alias is defined in `~/.bash_aliases` and uses the `strava_sync.sh` wrapper script:
- Location: `~/Projects/strava-fulcrum-bridge/strava_sync.sh`
- Takes a single argument: number of recent activities to sync
- Looks back 30 days for activities
- Can be used from any directory via SSH

**Adding the alias to a new session:**
If you open a new SSH session and `stravasync` is not recognized:
```bash
source ~/.bashrc
```

## Training Calendar Integration

In addition to syncing activities to Fulcrum, this application can generate and serve a subscribable iCalendar (.ics) file that combines your planned training workouts with completed Strava activities. This allows you to view your training plan and actual workouts in Apple Calendar, Google Calendar, or any calendar app that supports .ics subscriptions.

### Features

- **Planned Workouts**: Import your training plan from CSV and view scheduled workouts
- **Completed Activities**: Automatically match Strava activities with planned workouts
- **Real-time Stats**: See actual pace, heart rate, elevation, and duration for completed workouts
- **Extra Credit Tracking**: Unplanned workouts appear with a special indicator
- **Automatic Updates**: Calendar regenerates after each activity sync

### Quick Setup

1. **Import Your Training Plan:**
   ```bash
   cd ~/strava-fulcrum-bridge
   source venv/bin/activate
   python3 training_calendar/import_plan.py your_training_plan.csv
   ```

2. **Install the Calendar Server Service:**
   ```bash
   sudo cp training-calendar.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable training-calendar.service
   sudo systemctl start training-calendar.service
   ```

3. **Subscribe in Your Calendar App:**
   - iPhone/iPad: Settings → [Your Name] → iCloud → Calendar → Add Subscription
   - Mac: Calendar app → File → New Calendar Subscription
   - URL: `http://YOUR_PI_IP:8080/training_calendar.ics`
   - Or use: `http://raspberrypi.local:8080/training_calendar.ics`
   - Set refresh frequency to "Every hour"

### Calendar Event Types

- 🏃 **Planned Run** - Not yet completed
- 💪 **Planned Strength** - Not yet completed
- ✅ **Completed Workout** - Synced from Strava with actual stats
- ⭐ **Extra Credit** - Unplanned workout completed
- 🛌 **Rest Day** - All-day rest event

### Detailed Documentation

For complete setup instructions, troubleshooting, and advanced usage:
- **Full Guide**: See `CALENDAR_SETUP.md`
- **Quick Reference**: See `CALENDAR_QUICKREF.md`

### How It Works

1. You import your training plan CSV (dates, workout types, distances, notes)
2. The plan is stored in a SQLite database
3. When activities sync from Strava, they're matched with planned workouts
4. The calendar file (.ics) is regenerated with updated completion status
5. Your subscribed devices refresh hourly and show the updates

### Training Plan CSV Format

Your CSV should have these columns:
- `Week` - Training week number
- `Date` - MM-DD format
- `Day` - Day abbreviation (M, T, W, R, F, Sa, Su)
- `Workout Type` - Run, Burn Bootcamp, Rest, etc.
- `Details` - Workout description (e.g., "Easy trail run - Zone 2 HR")
- `Duration` - Planned duration (e.g., "30-35min", "60min")
- `Distance (mi)` - Planned distance in miles
- `Notes` - Additional notes or comments

See the `training_calendar/` directory for example files and scripts.

## Server Management & Maintenance

Once the `strava-bridge.service` is set up and running with `systemd`, you can manage it and perform routine maintenance using the following commands via SSH on your Raspberry Pi.

### Checking Server Status

*   **Check the current status of the service:**
    ```bash
    sudo systemctl status strava-bridge.service
    ```
    Look for `Active: active (running)`. Press `q` to exit the status view.

*   **View live logs from the service:**
    ```bash
    sudo journalctl -u strava-bridge.service -f
    ```
    Press `Ctrl+C` to stop following the logs.

*   **View all logs for the service:**
    ```bash
    sudo journalctl -u strava-bridge.service
    ```
    You can navigate this with arrow keys, Page Up/Down. Press `q` to exit. To see logs since the last boot:
    ```bash
    sudo journalctl -u strava-bridge.service -b
    ```

### Managing the Service

*   **Start the service (if it's stopped):**
    ```bash
    sudo systemctl start strava-bridge.service
    ```

*   **Stop the service:**
    ```bash
    sudo systemctl stop strava-bridge.service
    ```

*   **Restart the service (e.g., after making code changes or updating `.env`):**
    ```bash
    sudo systemctl restart strava-bridge.service
    ```
    *Note: If you only change the `.env` file, a restart is usually sufficient. If you change the Python code (`strava_webhook.py`) or `requirements.txt`, you'll need to pull changes (if applicable) and then restart the service.*

*   **Check if the service is enabled to start on boot:**
    ```bash
    sudo systemctl is-enabled strava-bridge.service
    ```
    (Should output `enabled`)

### Updating the Application Code

If you've made changes to the application code in your Git repository (or if you're pulling updates from the original repository if you forked it):

1.  **SSH into your Raspberry Pi.**
2.  **Navigate to the project directory:**
    ```bash
    cd ~/strava-fulcrum-bridge # Or your project path
    ```
3.  **(Optional) Stop the service before updating (good practice):**
    ```bash
    sudo systemctl stop strava-bridge.service
    ```
4.  **Pull the latest changes from your Git repository:**
    ```bash
    git pull origin main # Or your default branch name
    ```
5.  **Activate the virtual environment:**
    ```bash
    source venv/bin/activate
    ```
6.  **(If applicable) Update Python dependencies if `requirements.txt` has changed:**
    ```bash
    (venv) pip install -r requirements.txt
    ```
7.  **Deactivate the virtual environment (optional, but good to exit if done):**
    ```bash
    (venv) deactivate
    ```
8.  **Restart the service to apply changes:**
    ```bash
    sudo systemctl restart strava-bridge.service
    ```
9.  **Check the status and logs to ensure it started correctly.**

### System Maintenance (Raspberry Pi OS)

It's important to keep your Raspberry Pi's operating system and packages up to date for security and stability.

1.  **Update package lists and upgrade installed packages periodically (e.g., monthly):**
    ```bash
    sudo apt update
    sudo apt full-upgrade -y
    ```
2.  **Reboot if necessary:** Some updates (like kernel updates) may require a reboot. The system will usually inform you if a reboot is needed.
    ```bash
    sudo reboot
    ```
    Your `strava-bridge.service` should automatically start after the reboot if it's enabled.

### Checking Disk Space

If the application generates significant logs or stores other data, occasionally check disk space:
```bash
df -h
```

## Troubleshooting

### Duplicate Activities in Fulcrum

If you're seeing duplicate activities being created in Fulcrum:

1.  **Check for the `strava_activity_id` field:**
    - Log in to Fulcrum and open your form in the form builder
    - Verify there's a text field with data name `strava_activity_id`
    - If missing, add it as described in Phase 5, step 4

2.  **Verify the field ID in the code:**
    - The application expects the field to have data name `strava_activity_id`
    - The internal field ID (key) will be automatically discovered by the Fulcrum API
    - If you named the field something different, update `strava_webhook.py` and `sync_activities.py`

3.  **Test duplicate detection:**
    ```bash
    cd ~/Projects/strava-fulcrum-bridge
    source venv/bin/activate
    python3 sync_activities.py 1 --days 1
    ```
    - Run this command twice
    - The first time should sync the activity
    - The second time should skip it with message: "✓ Already exists in Fulcrum - skipping"

4.  **Restart the service after changes:**
    ```bash
    sudo systemctl restart strava-bridge.service
    ```

### Cron Job Not Running

If the automatic hourly sync isn't working:

1.  **Check crontab:**
    ```bash
    crontab -l
    ```
    - Verify the cron job includes `cd ~/strava-fulcrum-bridge &&` before the python command
    - The path should change to the project directory before running

2.  **Check cron logs:**
    ```bash
    tail -50 ~/Projects/strava-fulcrum-bridge/sync_cron.log
    ```
    - Look for error messages or "No such file or directory" errors
    - Verify activities are being detected and synced/skipped appropriately

3.  **Test the command manually:**
    ```bash
    cd ~/Projects/strava-fulcrum-bridge && ~/Projects/strava-fulcrum-bridge/venv/bin/python3 sync_activities.py 1 --days 1
    ```
    - If this works but cron doesn't, check your crontab syntax

