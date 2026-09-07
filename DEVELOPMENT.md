# Development notes

Branch: `feature/backend-postgres-flask`

The frontend remains a static site and now delegates authentication to the Flask API through `api.js`. Do not put database URLs, SMTP passwords, signing keys, or provider API keys in HTML, JavaScript, or committed configuration. Use environment variables and deployment secret storage.

For production, serve the static frontend and Flask API over HTTPS, use PostgreSQL, set `SESSION_COOKIE_SECURE=true`, configure SMTP for verification mail, run the SQL migration, and restrict `FRONTEND_ORIGINS` to the real site origin. The built-in SQLite fallback is intended only for tests or local smoke checks.
