# PaceLab architecture

PaceLab is a running analytics platform. The product question is whether a runner's fitness is actually improving — not a recreation of Garmin Connect.

This document records decisions that later phases must preserve.

## System shape

The repository is a monorepo:

- `frontend/` — React, TypeScript, Vite, Tailwind CSS
- `backend/` — FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL
- `docker-compose.yml` — `frontend`, `backend`, `postgres`

No Redis, Celery, or Kubernetes is used for the MVP.

## Phase 1 scope

Phase 1 establishes a runnable foundation:

- Docker Compose development stack
- PostgreSQL with persistent volume
- FastAPI application with structured errors and security headers
- `GET /health` (API process + database connectivity)
- Alembic migration pipeline
- React UI that reports health status

## Phase 2 scope

Phase 2 adds application authentication:

- `users`, `auth_sessions`, and `user_tokens` tables
- Register / login / logout / current user
- Argon2id password hashes (never returned by the API)
- Server-side sessions: the browser stores a random token in an HttpOnly cookie; only a SHA-256 hash is stored in PostgreSQL
- CSRF double-submit for mutating `/api` requests
- Email verification and password-reset token **architecture** (hashed tokens, recording email sender — no SMTP yet)

## Phase 3 scope

Phase 3 adds activity ingestion without live Garmin access:

- `activities`, `activity_samples`, and `provider_connections` tables
- `ActivityProvider` protocol with `MockActivityProvider` (real catalog) and `GarminActivityProvider` (architecture stub)
- Idempotent `sync_user_activities` keyed by `(user_id, provider, provider_activity_id)`
- Versioned activity API under `/api/v1/activities`
- Development seed: `python -m app.db.seed`

Analytics, dashboard charts, privacy tooling, and live Garmin OAuth remain later phases.

Time-series samples do **not** store latitude/longitude. GPS is sensitive location data and is not required for MVP pace/HR analytics. A future Garmin mapping can drop those fields even if the official API returns them.

`provider_connections` records `last_sync_at` only. Encrypted Garmin OAuth tokens belong on a later `GarminConnection` (or extra columns) and must never appear in API responses.

## Authentication model

PaceLab sessions are **not** JWTs in localStorage. A row in `auth_sessions` can be revoked on logout or password change. The API derives the current user from that session. Handlers must not trust a client-supplied `user_id`.

Future Garmin OAuth tokens will live on a `GarminConnection` owned by this same `User`. They will be encrypted at rest and never placed in the PaceLab session cookie or API responses.

## Garmin integration (future)

Garmin data must come from the official Garmin Connect Developer Program using OAuth 2.0.

The application will **not**:

- scrape Garmin Connect
- collect or store Garmin usernames or passwords
- use unofficial Garmin authentication
- invent Garmin API endpoints or credentials

Activity ingestion is isolated behind a provider interface:

- `MockActivityProvider` for development, tests, and seed data
- `GarminActivityProvider` as a stub until official developer credentials exist (Phase 7). The stub raises; it does not invent HTTP endpoints.

Until Garmin access is granted, PaceLab remains fully usable with mock data and optional FIT-file import.

OAuth client secrets and tokens will live in environment variables / encrypted database columns. They are never returned by the API and never written to logs.

## Security baseline already in place

- Secrets are environment variables; `.env` is gitignored; `.env.example` has placeholders only
- CORS is restricted to `FRONTEND_URL`
- Security headers on API responses
- OpenAPI docs disabled when `ENVIRONMENT=production`
- Production rejects debug mode and placeholder `SECRET_KEY` values
- Database access is async SQLAlchemy (parameterised queries)
- Docker images run as a non-root user (`pacelab`)
- Health checks do not expose stack traces

Session cookies, CSRF, Argon2id password hashing, and account endpoints are in place as of Phase 2. Privacy export/deletion and cookie-consent UI arrive later and must not weaken this baseline.

## Multi-user readiness

Every table that stores personal running data has an explicit `user_id` ownership column (`ON DELETE CASCADE`). API handlers take the current user from the authenticated session, never from a client-supplied `user_id`. Activity rows are unique per `(user_id, provider, provider_activity_id)` so two accounts can import the same mock ids without colliding, and a repeated sync cannot duplicate a run.
