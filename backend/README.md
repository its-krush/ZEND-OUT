# Zen'd Out backend

This branch adds a Flask API and PostgreSQL schema behind the existing static frontend. The existing visual design and page layout are intentionally preserved. The only necessary authentication change is an email field during registration and server-backed authentication.

## Local setup

1. Create PostgreSQL database/user and apply `migrations/001_initial.sql`.
2. Create a virtual environment, install `requirements.txt`, and copy `.env.example` to `.env`.
3. Set a long random `SECRET_KEY`, `DATABASE_URL`, `FRONTEND_ORIGINS`, and SMTP values. Never commit `.env`.
4. Run `flask --app app run --debug` from `backend/` and serve the repository root over HTTP, for example `python -m http.server 8000`.

The frontend sends same-origin credentialed requests to `/api`. For a separate frontend host, set `ZEN_API_BASE` before loading `api.js` and add that origin to `FRONTEND_ORIGINS`.

## Security decisions

Passwords are stored as scrypt hashes, never plaintext. Registration requires a valid email and a 12-character minimum password. Email verification tokens are signed, single-purpose, and expire after 24 hours. Authentication uses an HTTP-only, SameSite session cookie; production should set `SESSION_COOKIE_SECURE=true` behind HTTPS. Mutating requests use Flask-WTF CSRF protection, CORS is allowlisted, request bodies are size-limited, and authentication endpoints are rate-limited. Secrets and SMTP credentials are read only from environment variables.

## Migrations

Apply the migrations in order against the development database only: `001_initial.sql`, `002_password_reset_tokens.sql`, and `003_social.sql`. They are additive and do not drop or recreate existing tables. Do not run them against production automatically.

## Scope

The API exposes health, registration, email verification, login, logout, password reset, current-user, journal CRUD, and social feed/follow/like/comment endpoints. `001_initial.sql` covers the supplied ER diagram's users, roles/permissions, journaling/moods, social, notifications, sessions, reports, habits, puzzles, challenges, achievements, and library tables; migrations 002 and 003 add the reset-token and server-backed social constraints used by this pass. The puzzle game score widgets and screen-time chart remain browser-local UI state and have not been falsely presented as PostgreSQL-backed; they are the next isolated migration area if cross-browser persistence is required.
