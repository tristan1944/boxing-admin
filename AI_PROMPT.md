# Build Agent Prompt — Boxing Admin API (Backend-Only)

Use this document as your operating prompt when continuing the build. You have embeddings available for both domain data and code. Optimize your code style and structure for high-quality embeddings and semantic retrieval while keeping the codebase clean and maintainable.

## Mission
- Deliver a backend-only MVP for a boxing gym admin system.
- FastAPI + SQLAlchemy + Pydantic (v2) with SQLite by default; Postgres-ready.
- Token-based auth for all `/api/*` routes; open `/health`.
- Embed domain data and optionally code context to accelerate iterative development.

## Current State (Progress)
- App: `FastAPI` app with CORS, token auth, DB auto-create, observability (timing + error shape), and lifespan startup.
- DB: SQLite file in repo, SQLAlchemy models for Members, Events, Bookings, ClassTypes, Groups, FacebookCampaigns, Config, SystemLog, Embedding, StripeWebhook, StripeCustomer, Payment, Refund, WhatsAppMessage, WhatsAppStatusEvent, MemberVisit.
- Core Routers: health, campaigns, members, events, bookings, exports, analytics.
- Added Routers: embeddings (data vectors), code (ephemeral code vectors), devtools (npm clash guidance), class_types, groups, payments, stripe stub, whatsapp stub, qr check-in.
- Embeddings: provider switchable via env (fake|openai), background re-embedding on Members/Events create/update; backfill and search endpoints; fake provider now caches by text hash for determinism and speed.

## Tech/Config
- Env: `.env` supports `APP_API_TOKEN`, `APP_DATABASE_URL`, `APP_CORS_ORIGINS`, embeddings provider and OpenAI settings.
- Start: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.
- Seed: `python -m app.seed` (idempotent defaults).

## API Surface (stabilized)
- Health: `GET /health`
- Campaigns: `GET /api/campaigns.list`
- Members: `POST /api/members.create`, `POST /api/members.update`, `GET /api/members.list`
- Events: `POST /api/events.create`, `POST /api/events.update`, `GET /api/events.list`
- Bookings: `POST /api/bookings.create`, `POST /api/bookings.approve`, `POST /api/bookings.cancel`, `GET /api/bookings.list`
- Exports: `GET /api/export.members.csv`, `GET /api/export.events.csv`, `GET /api/export.bookings.csv`
- Analytics: `GET /api/analytics.summary`
- Embeddings (data): `POST /api/embeddings.backfill`, `GET /api/embeddings.search`
- Code embeddings (ephemeral): `POST /api/code/backfill`, `POST /api/code/search`
- Devtools: `GET /api/dev/npm.dedupe-plan`
- ClassTypes: `POST /api/class_types.create`, `POST /api/class_types.update`, `GET /api/class_types.list`
- Groups: `POST /api/groups.create`, `POST /api/groups.update`, `GET /api/groups.list`
- Payments: `POST /api/payments.create`, `GET /api/payments.list`
- Refunds: `POST /api/refunds.create`, `GET /api/refunds.list`
- Stripe: `POST /api/stripe.webhook` (stub storing payloads/types)
- WhatsApp: `POST /api/whatsapp.sendGroup`, `POST /api/whatsapp.status`

## Embeddings — How to Use and Optimize Code for Them
- Data embeddings: Persisted vectors for Members, Events, ClassTypes in table `embeddings`. Re-embed on create/update. Backfill via `/api/embeddings.backfill`.
- Code embeddings: Ephemeral, stateless. Generate vectors for selected extensions from the workspace via `/api/code/backfill` and search with `/api/code/search`. These do not touch saved DB state and are isolated from Cursor’s own code intelligence.
- Provider: `APP_EMBEDDINGS_PROVIDER=fake|openai`. For OpenAI, use `APP_OPENAI_API_KEY` and `APP_OPENAI_EMBEDDINGS_MODEL`.

### Embedding-optimized code style (allowed and encouraged)
- Add concise, high-signal docstrings at:
  - Top of module: purpose, key responsibilities, inputs/outputs, external effects.
  - Public functions/classes: what it does, when to use, expected inputs/outputs, constraints.
- Prefer meaningful names for files, symbols, and arguments.
- Add brief “embedding anchors” in docstrings where helpful:
  - EMBED_SUMMARY: a one-paragraph summary.
  - EMBED_TAGS: comma-separated keywords.
  - EMBED_IGNORE: mention for large or generated content to be ignored by retrieval.
- Keep anchors minimal and semantically rich; do not narrate implementation steps.
- You may place such docstrings/anchors anywhere they improve retrieval (e.g., helpers used across modules) without clutter.

Example anchor (docstring excerpt):
"""
EMBED_SUMMARY: Capacity-aware booking create/approve workflow with group-based approval overrides.
EMBED_TAGS: bookings, capacity, approval, events, groups
"""

## Guardrails
- Do not embed secrets. Ignore heavy/generated dirs: `node_modules`, `.venv`, `.git`, `dist`, `build`, `.next`.
- Keep `/api/*` behind Bearer token from `APP_API_TOKEN`.
- Keep schema stable; add migrations later (Alembic) when switching to Postgres.
- Keep code embeddings ephemeral to avoid clashing with Cursor’s own indexing.

## Development Runbook
- Install deps: `pip install -r requirements.txt`
- Seed: `python -m app.seed`
- Start: `uvicorn app.main:app --reload --port 8000`
- Data backfill: `curl -H "Authorization: Bearer $TOKEN" -X POST http://127.0.0.1:8000/api/embeddings.backfill`
- Data search: `curl -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8000/api/embeddings.search?entity_type=member&q=cardio"`
- Code backfill: `curl -H "Authorization: Bearer $TOKEN" -X POST "http://127.0.0.1:8000/api/code/backfill?exts=.py,.md&ignores=**/node_modules/**,**/.venv/**"`
- Code search: `curl -H "Authorization: Bearer $TOKEN" -X POST "http://127.0.0.1:8000/api/code/search?q=booking%20capacity&exts=.py"`

## Conventions & Style
- Python: explicit types for public APIs; guard clauses; shallow nesting; clear naming; multi-line for readability.
- Docstrings: explain why and the contract; keep how minimal.
- DB: use `onupdate=datetime.utcnow` for `updated_at` columns.
- API: stable shapes; pagination via `page/page_size`; filters explicit; CSV exports with strict headers.

## Backlog (Next Actions)
- Stripe webhook updaters: parse event types to transition `Payment.status`, populate provider IDs, create `Refund` rows on refund events; add tests.
- WhatsApp provider callbacks: accept provider variants for delivered/read/error; persist `WhatsAppStatusEvent` and update `WhatsAppMessage.status`; add tests.
- Analytics totals (no time bucketing yet): totals for payments, refunds, whatsapp delivered/read; expose minimal API and tests.
- Members visits: extend analytics using `MemberVisit` rows; shape KPIs without time buckets.
- Rate limiting: optional enable via env and tested (already wired).
- Postgres/Alembic migration plan; consider pgvector.

## Working Agreements for the Agent
- You may add docstrings and EMBED_* anchors wherever they improve retrieval.
- Prefer adding or updating docstrings over inline comments.
- Keep endpoints small and composable; re-use helpers.
- Maintain auth on all `/api/*`.
- Keep code embeddings isolated and ephemeral; never persist them in the DB.
- Prefer adding EMBED_SUMMARY/EMBED_TAGS docstrings to new models/modules and math helpers to anchor formulas before introducing time buckets.
- When modifying schema, also update Pydantic models and routers consistently.

## Objective Recap
- Deliver a robust backend MVP with clean endpoints and stable models.
- Use embeddings (data + optional code) to accelerate reasoning and search.
- Keep an easy path to Postgres/Django migration by maintaining stable field names and API contracts.
