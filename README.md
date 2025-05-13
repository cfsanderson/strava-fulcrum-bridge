# Strava → Fulcrum Webhook Bridge

This project lets you automatically receive new Strava activities (via webhook), fetch their details, and create records in Fulcrum with the activity data and route.

---

## 🚀 Quick Start Guide

This project lets you automatically receive new Strava activities (via webhook), fetch their details, and create records in Fulcrum.

---

## Local Development Setup

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

5. **Run the quickstart script (recommended):**
    ```sh
    ./quickstart.sh
    ```
    This will:
    - Install dependencies
    - Set up your environment
    - Run basic tests
    - Register the Strava webhook (if `strava-auth.sh` is present)
    - Start the app

6. **Complete the Strava OAuth flow:**
    - Start your app locally (`python strava_webhook.py` or via quickstart)
    - Open this URL in your browser (replace values as needed):
      ```
      https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost:5055/exchange_token&approval_prompt=force&scope=activity:read_all
      ```
    - Authorize the app. The `/exchange_token` endpoint will handle the code exchange and save `.strava-tokens.json`.

7. **Test locally:**
    - Create a new Strava activity and confirm it triggers the webhook and creates a Fulcrum record.

---

## Production Deployment (Render.com)

1. **Push your code to GitHub.**

2. **Create a new Web Service on [Render.com](https://render.com/):**
    - Connect your GitHub repo.
    - Configure:
      - **Environment:** Python 3
      - **Build Command:** *(leave blank; Render will use requirements.txt)*
      - **Start Command:** `gunicorn strava_webhook:app`
      - **Branch:** main (or your preferred branch)
    - Add environment variables from your `.env` file:
      - `STRAVA_CLIENT_ID`
      - `STRAVA_CLIENT_SECRET`
      - `FULCRUM_API_TOKEN`
      - `FULCRUM_FORM_ID`
      - (Optional) `CALLBACK_URL`

3. **Deploy and get your public URL** (e.g., `https://your-app.onrender.com`).

4. **Register the Strava webhook:**
    - Update your Strava webhook subscription to use your Render.com public URL (e.g., `https://your-app.onrender.com/strava-webhook`).
    - You can use the `strava-auth.sh` script with the correct environment variables, or register manually via the Strava API.

5. **Complete the Strava OAuth flow in production:**
    - Open this URL (replace with your actual values):
      ```
      https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=https://your-app.onrender.com/exchange_token&approval_prompt=force&scope=activity:read_all
      ```
    - Authorize the app. The `/exchange_token` endpoint will handle the code exchange and save `.strava-tokens.json` on your Render.com server.

6. **Test your deployment:**
    - Create a new Strava activity.
    - Confirm records appear in Fulcrum.
    - Check logs in the Render.com dashboard for any errors.

---

## Notes & Security

- **Never commit `.strava-tokens.json` or any secrets to your repository.**
- Use environment variables for all secrets in production.
- The `/exchange_token` endpoint is for OAuth only; `/strava-webhook` is for webhook events.
- You can re-run the OAuth flow at any time to refresh your tokens.

---

## Troubleshooting

- If you see `Token file .strava-tokens.json not found!` in logs, you must complete the OAuth flow in your production environment.
- If you see `already exists` when registering the webhook, delete the old subscription and register again.
- Check Render.com logs for errors if Fulcrum records are not created.

---

For questions or help, open an issue or PR!

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
