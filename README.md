# Boxing Admin — FastAPI backend (MVP)

This repo now contains a FastAPI-based backend with SQLite by default (Postgres-ready). It implements token-based auth and core endpoints for Members, Events, Bookings, CSV exports, and a basic analytics summary.

## Quick start

1. Create a virtualenv and install dependencies:

```bash
python3 -m venv /Users/tristan/app/boxing-admin/.venv
/Users/tristan/app/boxing-admin/.venv/bin/pip install -r /Users/tristan/app/boxing-admin/requirements.txt
```

2. Create your `.env` (optional; defaults are reasonable for dev). Example:

```bash
cat > /Users/tristan/app/boxing-admin/.env <<'ENV'
APP_API_TOKEN=dev-token
APP_CORS_ORIGINS=*
APP_RATE_LIMIT_ENABLED=false
APP_RATE_LIMIT_PER_MINUTE=600
APP_EMBEDDINGS_PROVIDER=fake
APP_OPENAI_API_KEY=
APP_OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small
APP_EMBEDDINGS_DIMENSIONS=64
APP_QR_TOKEN=dev-qr-token
# APP_DATABASE_URL=sqlite:////Users/tristan/app/boxing-admin/boxing_admin.db
# APP_DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/boxing
ENV
```

3. Run the API server:

```bash
/Users/tristan/app/boxing-admin/.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The default API token is `dev-token`. Pass it as `Authorization: Bearer dev-token`.

## Endpoints

- Health: `GET /health`
- Campaigns: `GET /api/campaigns.list`
- Members: `POST /api/members.create`, `POST /api/members.update`, `GET /api/members.list`
- Events: `POST /api/events.create`, `POST /api/events.update`, `GET /api/events.list`
- Bookings: `POST /api/bookings.create`, `POST /api/bookings.approve`, `POST /api/bookings.cancel`, `GET /api/bookings.list`
- Exports: `GET /api/export.members.csv`, `GET /api/export.events.csv`, `GET /api/export.bookings.csv`
- Analytics: `GET /api/analytics.summary`

All `/api/*` endpoints require a bearer token.

## Database

SQLite DB file is created at `boxing_admin.db` in the repo root by default. Switch to Postgres by setting `APP_DATABASE_URL` in `.env`, e.g.:

```
APP_DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/boxing
```

Tables are auto-created on startup. No migrations yet (MVP).
