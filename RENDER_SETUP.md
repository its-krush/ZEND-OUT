# Zen'd Out on Render

This repository is deployed as **one Render Web Service**. Flask serves the HTML, JavaScript, images, API, sessions, and email-verification flow from the same HTTPS origin. Render also creates the PostgreSQL database from `render.yaml`.

## 1. Push or select the correct branch

Use the branch containing the backend files: `feature/render-production` after the fixes in this commit. If you prefer `main`, merge this branch into `main` first. The repository must contain `render.yaml`, `requirements.txt`, `backend/`, `api.js`, `auth-guard.js`, and `verify-email.html`.

## 2. Create the Render Blueprint

In Render, choose **New → Blueprint**, connect `its-krush/ZEND-OUT`, and select the branch containing this file. Render reads `render.yaml` and creates:

| Resource | Value |
|---|---|
| Web service | `zendout` |
| Runtime | Python |
| Plan | Free |
| Database | `zendout-db`, Free PostgreSQL |
| Health check | `/api/health` |
| Build command | `pip install -r requirements.txt` |
| Start command | `python backend/migrate.py && cd backend && gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60 wsgi:app` |

The first deployment may take a few minutes. Do not manually run `db.drop_all()` or delete the production database.

## 3. Set environment variables

Open the **zendout Web Service → Environment** page. The Blueprint creates the variables marked as generated or secret. Set these values there, not in HTML, JavaScript, GitHub, or a committed `.env` file.

| Variable | Value | Where it comes from |
|---|---|---|
| `FLASK_ENV` | `production` | Exact text |
| `SECRET_KEY` | A long random secret | Use Render **Generate**; never reuse a public value |
| `DATABASE_URL` | Automatically linked to `zendout-db` | Created by `render.yaml`; do not replace with SQLite |
| `AUTO_CREATE_DB` | `false` | Exact text; migrations run from the start command |
| `SESSION_COOKIE_SECURE` | `true` | Exact text; Render provides HTTPS |
| `EMAIL_VERIFICATION_REQUIRED` | `true` | Exact text |
| `FRONTEND_BASE_URL` | `https://zendout.onrender.com` | Replace with the exact URL Render gives the service; no trailing slash |
| `MAIL_SERVER` | SMTP hostname from your email provider | Example: provider SMTP host |
| `MAIL_PORT` | `587` | TLS submission port for the provider |
| `MAIL_USERNAME` | SMTP username | Usually the provider account or generated SMTP username |
| `MAIL_PASSWORD` | SMTP password or provider SMTP token | Store as a secret in Render |
| `MAIL_DEFAULT_SENDER` | An allowed sender address | Example: `no-reply@your-domain.com` |

If you use a custom domain, set `FRONTEND_BASE_URL` to that HTTPS domain instead of the `onrender.com` URL. The sender address must be accepted by your SMTP provider; otherwise verification and password-reset messages will not be delivered.

## 4. Deploy and verify the service

After saving the variables, trigger **Manual Deploy → Deploy latest commit**. Confirm these checks in the deployed URL:

1. Open `https://YOUR-RENDER-HOST.onrender.com/`; the Zen'd Out login page should load.
2. Open `https://YOUR-RENDER-HOST.onrender.com/api/health`; it should return `{"status":"ok"}`.
3. Create an account with a real email address and a password of at least 12 characters.
4. Confirm the email arrives, open its verification link, and check that the page says **Email verified**.
5. Log in using either the username or email address.
6. Create a journal entry, reload the page, and confirm it remains after reload and from another browser session.
7. Test **Forgot password?** and confirm the reset link arrives.
8. Test the journal, puzzle, social, and analytics pages while logged in.

## 5. Important production notes

The free Render web service and free database are suitable for a demonstration or hobby deployment but may sleep or have resource limits. Before production use, configure database backups, a custom domain, an authenticated SMTP provider, and a paid or persistent plan if the app needs reliable always-on availability. Never paste SMTP passwords, `SECRET_KEY`, or a database URL into frontend files.

For a separate frontend host, set `ZEN_API_BASE` before loading `api.js`, set `FRONTEND_ORIGINS` to the exact HTTPS frontend origin, and use secure cross-origin cookie settings. The included one-service Blueprint is recommended because it avoids that extra CORS and cookie configuration.
