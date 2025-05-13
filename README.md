# Strava → Fulcrum Webhook Bridge

This project lets you automatically receive new Strava activities (via webhook), fetch their details, and create records in Fulcrum with the activity data and route.

---

## 🚀 Onboarding

Follow these steps to get up and running quickly:

1. **Clone the repository:**
    ```sh
    git clone https://github.com/cfsanderson/strava-fulcrum-bridge.git
    cd strava-fulcrum-bridge
    ```

2. **Install dependencies:**
    ```sh
    python -m pip install -r requirements.txt
    ```

3. **Create your Strava API application:**
    - Go to [Strava API settings](https://www.strava.com/settings/api)
    - Register your app and note your **Client ID** and **Client Secret**

4. **Set up your environment variables:**
    - Copy `.env.example` to `.env` and fill in your real values:
      ```sh
      cp .env.example .env
      # Edit .env and set STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, FULCRUM_API_TOKEN, FULCRUM_FORM_ID
      ```
    - For production (Render.com), set these variables in the Render dashboard.

5. **Deploy to Render.com (recommended for production):**
    - Push your code to GitHub.
    - Create a new Web Service on [Render.com](https://render.com/).
    - Set the environment variables from your `.env` file in the Render dashboard.
    - Render will auto-detect and run your app via the `Procfile`.
    - After deploy, you’ll receive a public HTTPS URL (e.g., `https://your-app.onrender.com/strava-webhook`).

6. **Register the Strava webhook:**
    - Update your Strava webhook subscription to use your Render.com public URL.
    - You can use the `strava-auth.sh` script, which now uses environment variables for all secrets.

7. **Complete the Strava OAuth flow:**
    - See the "Complete the Strava OAuth Flow" section below for details.

---

## Setup

### 1. Clone the Repo

```sh
git clone https://github.com/cfsanderson/strava-fulcrum-bridge.git
cd strava-fulcrum-bridge
```

### 2. Install Requirements

```sh
python -m pip install flask requests polyline gpxpy
```

### 3. Create Strava API Application

-   Go to [https://www.strava.com/settings/api](https://www.strava.com/settings/api)
-   Register your app and note your **Client ID** and **Client Secret**.

### 4. Set Environment Variables

Set the following environment variables:

*   `STRAVA_CLIENT_ID`
*   `STRAVA_CLIENT_SECRET`
*   `FULCRUM_API_TOKEN`
*   `FULCRUM_FORM_ID`

For local development, you can set these variables in your terminal or create a `.env` file. For production deployment on Render.com, set these variables in your Render.com dashboard.

### 5. Local Quickstart (Recommended)

For the fastest onboarding, use the provided quickstart script:

```sh
./quickstart.sh
```

This script will:
- Install dependencies
- Set up your environment (copy `.env.example` if needed)
- Run basic tests
- Register the Strava webhook (if `strava-auth.sh` is present)
- Start the app with Gunicorn (production) or Flask (dev)

If you prefer to run steps manually, see below.

For manual local development:
```sh
python strava_webhook.py
```

For production deployment on Render.com, follow the instructions below.

### 6. Deploy to Render.com

1. Go to [Render.com](https://render.com/) and log in.
2. Click "New +" → "Web Service".
3. Connect your GitHub repo and select the `strava-fulcrum-bridge` repository.
4. Configure the service:
   - **Environment:** Python 3
   - **Build Command:** *(leave blank; Render will use requirements.txt)*
   - **Start Command:** `gunicorn strava_webhook:app`
   - **Branch:** main (or your preferred branch)
5. In the "Environment" section, add each variable from your `.env` file:
   - `STRAVA_CLIENT_ID`
   - `STRAVA_CLIENT_SECRET`
   - `FULCRUM_API_TOKEN`
   - `FULCRUM_FORM_ID`
   - (Optional) `CALLBACK_URL`
6. Click "Create Web Service" to deploy.
7. Wait for the build to finish. You’ll see logs and a status bar. If the build fails, check logs for missing dependencies or typos.
8. Copy your public URL (e.g., `https://your-app.onrender.com/strava-webhook`).

---

### 7. After Deploying

1. **Register your Strava webhook:**
   - Set your callback URL to your Render.com public endpoint (e.g., `https://your-app.onrender.com/strava-webhook`).
   - You can use the provided script:
     ```sh
     export CALLBACK_URL=https://your-app.onrender.com/strava-webhook
     ./strava-auth.sh
     ```
   - Or register manually via the Strava API.

2. **Complete the Strava OAuth flow:**
   - Follow the "Complete the Strava OAuth Flow" section below to authorize your Strava account and obtain an access token.

3. **Test your deployment:**
   - Trigger a new activity in Strava.
   - Confirm new records appear in Fulcrum.
   - Check logs in the Render.com dashboard for any errors.

---

### 7. Register the Webhook

Edit and run `strava-api.sh` with your actual Render.com URL:

```sh
./strava-api.sh
```

### 8. Complete the Strava OAuth Flow

1.  Build an authorize URL:
    ```
    https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=activity:read_all
    ```
2.  Open in your browser, log in, and click Authorize.
3.  Copy the code from the redirect URL.
4.  Exchange the code for an access token:
    ```sh
    curl -X POST https://www.strava.com/oauth/token \
      -F client_id=YOUR_CLIENT_ID \
      -F client_secret=YOUR_CLIENT_SECRET \
      -F code=YOUR_CODE \
      -F grant_type=authorization_code
    ```
5.  Save your access token for use in API calls.

---

## Usage

-   When you create a new Strava activity, the webhook will trigger, fetch the activity details, and (optionally) create a Fulcrum record.
-   You can customize which activity fields are sent to Fulcrum in `strava_webhook.py`.

---

## Security

**Never commit your secret files!**  
Add sensitive files to your `.gitignore` to keep them out of version control.

For local development, use a tool like `ngrok` to create a secure tunnel to your local server.

For production deployment on Render.com, follow best practices for securing your environment variables and access tokens.

---

## Contributing

PRs and issues welcome!

---

## License

MIT (or your choice)
