# Progress — Boxing Admin API

## Objective
Backend-only MVP for a boxing gym admin system with token auth, SQLite dev DB (Postgres-ready), core CRUD & analytics, CSV exports, and embeddings (data + code) to accelerate development and search.

## Current Status
- Server: FastAPI running with CORS, token auth, request timing + error shape, rate limit wiring (toggleable).
- Database: SQLite auto-created; models for Members, Events, Bookings, ClassTypes, Groups, FacebookCampaigns, SystemLog, Config, Embedding, StripeWebhook, StripeCustomer, Payment, Refund, WhatsAppMessage, WhatsAppStatusEvent, MemberVisit.
- Endpoints: health, campaigns, members, events, bookings, exports, analytics, class_types, groups, payments, refunds, embeddings (data), code embeddings (ephemeral), devtools (npm dedupe plan), stripe (stub), whatsapp (stub+status), qr check-in (prototype).
- Embeddings: provider fake|openai via env; background re-embed on member/event create/update; backfill and search endpoints; fake provider cached for repeat texts.
- Prompt: AI_PROMPT.md created with embeddings-aware conventions and runbook.

## Recent Fixes
- Lifespan startup replaced deprecated on_event. Added observability middleware (timing header) and consistent error shape.
- CSV export headers emitted even with empty datasets.
- Replaced `| None` with `Optional[...]` for Python 3.9.
- Added tests: user flow, negative cases, embeddings/code embeddings, payments/refunds, analytics math, whatsapp status, pagination/filters, smoke. All green.

## Next Actions
- Stripe webhook updaters: status transitions, provider IDs, refund creation; tests.
- WhatsApp provider callback variants (delivered/read/error); tests.
- Analytics totals endpoints (no time buckets yet) for payments/refunds/whatsapp.
- Members visit analytics KPIs (no time buckets yet).
- Postgres/Alembic planning; pgvector path.

## Quick Commands
- Start: `uvicorn app.main:app --reload --port 8000`
- Seed: `python -m app.seed`
- Data embedding backfill: `curl -H "Authorization: Bearer $TOKEN" -X POST http://127.0.0.1:8000/api/embeddings.backfill`
- Code embedding backfill: `curl -H "Authorization: Bearer $TOKEN" -X POST "http://127.0.0.1:8000/api/code/backfill?exts=.py,.md&ignores=**/node_modules/**,**/.venv/**"`
- Run tests: `/Users/tristan/app/boxing-admin/.venv/bin/pytest -q`
