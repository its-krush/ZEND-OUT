# Deployment

The repository is deployable as one Flask WSGI service with Gunicorn: Flask serves both `/api/*` and the existing static HTML/image files. Set the following deployment secrets and environment variables; never commit `.env` or paste real values into HTML/JavaScript:

The dependency file is intentionally at the repository root as `requirements.txt`, because Render, Heroku, and most Python buildpacks run `pip install -r requirements.txt` from the repository root.

The repository also includes `render.yaml`. Use **New → Blueprint** in Render and select this repository/branch. Render will create the web service and PostgreSQL database, generate `SECRET_KEY`, set the build/start commands, and preserve environment values on later Blueprint syncs. Render will prompt for the SMTP values marked `sync: false` once; those credentials must remain secret and cannot safely be committed to GitHub.

```env
FLASK_ENV=production
SECRET_KEY=<long-random-secret>
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<database>
FRONTEND_ORIGINS=https://your-frontend.example
FRONTEND_BASE_URL=https://your-frontend.example
SESSION_COOKIE_SECURE=true
EMAIL_VERIFICATION_REQUIRED=true
MAIL_SERVER=<smtp-host>
MAIL_PORT=587
MAIL_USERNAME=<smtp-user>
MAIL_PASSWORD=<smtp-password>
MAIL_DEFAULT_SENDER=no-reply@your-domain.example
```

Deploy the service with the included `Procfile` or equivalent command:

```bash
cd backend
gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60 wsgi:app
```

The recommended beginner deployment is this single-service setup because it avoids cross-origin cookie configuration. If the frontend is hosted separately, set `window.ZEN_API_BASE` before loading `api.js` and list the exact frontend origin in `FRONTEND_ORIGINS`.

Apply migrations manually, in order, to the intended development or production database using a migration approval process:

```bash
psql "$DATABASE_URL" -f backend/migrations/001_initial.sql
psql "$DATABASE_URL" -f backend/migrations/002_password_reset_tokens.sql
psql "$DATABASE_URL" -f backend/migrations/003_social.sql
psql "$DATABASE_URL" -f backend/migrations/004_user_activity.sql
```

These migrations are additive. Do not use `db.drop_all()`, do not reset the database, and do not run production migrations automatically from application startup. Ensure the platform provides HTTPS, PostgreSQL backups, restricted database network access, and SMTP credentials through its secret manager.
