# PaceLab architecture

PaceLab is a running analytics platform. The product question is whether a runner's fitness is actually improving — not a recreation of Garmin Connect.

This document records decisions that later phases must preserve. **Phase 9 is implemented** (friend-scale public HTTPS, SMTP, operator runbook). Live Garmin OAuth, billing, and Kubernetes are not started.

## System shape

The repository is a monorepo:

- `frontend/` — React, TypeScript, Vite, Tailwind CSS
- `backend/` — FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL
- `docker-compose.yml` — laptop development (`frontend`, `backend`, `postgres`)
- `docker-compose.prod.yml` — friend-scale VPS (`caddy`, `frontend`, `backend`, `postgres`)

No Redis, Celery, or Kubernetes is used. Rate limits are in-process (one API worker in production).

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

## Phase 4 scope

Phase 4 adds a personal dashboard and richer activity views:

- Authenticated home dashboard answering “How is my running going?”
- Last-7-day volume, recent runs, and a pace/heart-rate chart over recent activities
- Slots for 5K estimate, easy pace, and aerobic efficiency (filled with real payloads in Phase 5)
- Activity history with date and type filters plus server-side pagination
- Activity detail with summary stats and pace, heart-rate, and pace-versus-HR charts

Charts use Recharts 3 (React SVG components with built-in tooltips). `react-is` is required as a peer of that library. No GPS is stored or drawn.

Date filters on `GET /api/v1/activities` are inclusive calendar dates interpreted in UTC (`from_date` start of day through end of `to_date`).

Time-series samples do **not** store latitude/longitude. GPS is sensitive location data and is not required for MVP pace/HR analytics. A future Garmin mapping can drop those fields even if the official API returns them.

`provider_connections` records `last_sync_at` only. Encrypted Strava OAuth tokens live on `strava_connections` and must never appear in API responses. Garmin tokens remain deferred.

## Phase 5 scope

Phase 5 adds dedicated running analytics (never inside API routes):

- Aerobic efficiency: moving speed / heart rate on easy/moderate runs, with Improving / Stable / Not enough data copy
- Easy Running page: configurable heart-rate band (default 140–150 bpm, query parameter, optional browser storage)
- Trends page: pace, heart rate, weekly distance, frequency, pace at comparable HR, with range presets
- Isolated 5K estimate (`performance_prediction.estimate_5k_time`, Riegel scaling)
- Dashboard placeholders replaced with those metrics when data exists

The heart-rate band is a query parameter (`hr_min`, `hr_max`; default 140–150). The UI may remember it in `localStorage` and must send it on Easy Running, Trends, and the dashboard easy-pace card. It is not persisted in PostgreSQL and is not a personal Zone 2.

APIs: `GET /api/v1/analytics/easy-running`, `GET /api/v1/analytics/trends`, `GET /api/v1/analytics/aerobic-efficiency`. Dashboard calls the same services rather than reimplementing the maths.

### Easy running

A run is included when it is a run type **and** either its activity-average heart rate sits in the requested band, or it has enough moving samples whose heart rate sits in that band. Aggregates prefer those in-band samples. Pace at a comparable heart rate scales observed pace to the midpoint of the band, assuming speed is roughly proportional to heart rate over easy/moderate running. That adjustment is for comparability, not a physiological model.

### Trends

`range` is one of `4w`, `8w` (default), `3m`, `6m`, `1y`, `all`. Weekly distance and frequency use Monday-based UTC weeks. Comparable-pace series uses the same heart-rate band as Easy Running.

### Aerobic efficiency

For each run-type activity, pause samples (speed ≤ 0.4 m/s) and implausible heart rates (outside 80–220 bpm) are dropped. Remaining samples give mean moving speed and mean heart rate. The score is **mean speed (m/s) / mean heart rate**. Higher is more speed at a similar heart rate. Efforts with mean HR above 168 bpm are excluded so hard sessions are not mixed with easy/moderate running. Direction compares the first half of qualifying runs with the last half; a 3% rise is “improving”. This is an application metric, not a VO2 or medical test.

### 5K estimate

`estimate_5k_time` scales recent 3–16 km runs with Riegel’s formula `T * (5000 / D) ** 1.06`, then takes the median of the three fastest of those times. At least two qualifying runs in 56 days are required. The number is an estimate, not a race prediction. A later model can replace the function body without changing the API shape (`available`, `estimated_seconds`, `note`).

## Phase 6 scope

Phase 6 adds privacy controls that do not weaken the Phase 2–5 security baseline:

- `GET /api/v1/privacy/export` — JSON file of the current user's PaceLab data (not a Garmin dump)
- `POST /api/v1/privacy/running-data/delete` — delete activities, samples, and this user's provider_connections; keep the account
- `POST /api/v1/privacy/account/delete` — hard-delete the user (CASCADE); clear session and CSRF cookies
- `POST /api/v1/privacy/providers/{provider}/disconnect` — delete that user's `provider_connections` row; for `strava`, also drop `strava_connections` and revoke the Strava token. Does not delete activity history. Not a Garmin disconnect.
- `GET /api/v1/privacy/connections` — provider name and `last_sync_at` for the settings UI

Identity always comes from `pacelab_session`. Destructive POSTs require CSRF plus the current password (`extra="forbid"`). Export and delete are rate-limited per user outside the test environment.

Export assembly lives in `app/services/privacy.py` (schema documented there). The file includes public account fields (including `updated_at`), activities with samples, and provider name / last sync. It excludes `password_hash`, `auth_sessions`, `user_tokens`, CSRF/session secrets, `SECRET_KEY`, other users, and invented OAuth token fields. Samples have no GPS columns.

Disconnect does **not** wipe activity history. Deleting running data does. There is no `deleted_at` / soft-delete. No new privacy tables: cookie Analytics/Marketing choices are stored in `localStorage` (same pattern as the heart-rate band). Necessary cookies (`pacelab_session`, `pacelab_csrf`) cannot be disabled. Optional categories default to off and do not inject scripts or pixels.

Draft public pages: `/privacy`, `/cookies`, `/terms`. They are marked “Draft for legal review. Not legal advice.” and do not claim GDPR/CCPA certification.

## Phase 7 scope

Phase 7 adds FIT-file import so Garmin-recorded runs can enter PaceLab without live Garmin APIs:

- `POST /api/v1/activities/import/fit` — multipart upload of `.fit` / `.fit.gz` (session user only)
- Parse in memory with Garmin’s official FIT Python SDK; original bytes are not stored
- Persist on existing `activities` / `activity_samples` with `provider = "fit"`
- Drop latitude, longitude, and other GPS fields; no new columns
- Idempotent via UNIQUE `(user_id, provider, provider_activity_id)` (session identity, else SHA-256 of bytes)
- Record `provider_connections.last_sync_at` for `fit` on a successful import (last import, not OAuth)
- Mock sync and seed remain; `GarminActivityProvider` stays a stub; official Strava OAuth is Phase 8

Official Garmin Connect Developer Program access for new apps is paused as of 2026-08. FIT upload is a file import from the watch or Garmin Connect, not a live Garmin link.

## Phase 8 scope

Phase 8 adds official Strava OAuth so PaceLab can pull a user’s activities without pretending to be a Garmin partner:

- `GET /api/v1/strava/connect` — 302 to Strava’s authorize URL (`activity:read_all`); 501 if client id/secret/redirect or `ENCRYPTION_KEY` is unset
- `GET /api/v1/strava/callback` — authorization-code exchange; `state` bound to the PaceLab session; then redirect to Settings
- `POST /api/v1/strava/sync` — pull recent Strava activities into existing tables via `StravaActivityProvider` + `sync_user_activities`
- `GET /api/v1/strava/status` — configured / connected / needs_reconnect / last_sync_at (never tokens)
- Tokens on `strava_connections` (Fernet-encrypted access + refresh). `provider_connections` still holds `last_sync_at` only
- Disconnect `provider=strava` deletes the token row, revokes via `POST https://www.strava.com/oauth/revoke`, keeps activity history
- First sync: last 90 days, at most 3 list pages of 30, streams for at most 40 activities
- Incremental sync uses `after` from last successful Strava `last_sync_at` / newest stored Strava `started_at`
- Drop `latlng` and map polylines; indoor/treadmill runs still import
- `POST /api/v1/activities/sync` remains mock (or the Garmin stub). FIT upload stays

PaceLab is not a Strava or Garmin partner. Connecting Strava is “connected to Strava”, not “connected to Garmin”.

## Phase 9 scope

Phase 9 makes PaceLab reachable on the public internet for the operator and a handful of friends:

- One public HTTPS origin (Caddy + Let’s Encrypt) in front of the existing production Docker images
- SMTP transactional mail (`SmtpEmailSender`); production refuses to boot without SMTP
- Development still uses `RecordingEmailSender` when SMTP env is empty (Account-page outbox)
- Operator runbook: `docs/deploy.md` (domain, DNS, VPS, secrets, Strava callback, backups)
- Mock “sync sample runs” and the in-memory outbox are development-only

This is **friend-scale**, not hyperscale. Scale-up (managed Postgres, Redis rate limits, Strava webhooks, more workers) is documented in `docs/deploy.md` and is not implemented.

Ingestion: mock / fit / strava / garmin-stub (unchanged)

Hosting:

- development — Docker Compose on the operator laptop
- production (Phase 9) — single public HTTPS origin, friend-scale, real SMTP
- later — managed DB, shared rate limits, Strava webhooks, more workers

## Authentication model

PaceLab sessions are **not** JWTs in localStorage. A row in `auth_sessions` can be revoked on logout or password change. The API derives the current user from that session. Handlers must not trust a client-supplied `user_id`.

Future Garmin OAuth tokens will live on a `GarminConnection` owned by this same `User`. They will be encrypted at rest and never placed in the PaceLab session cookie or API responses. That work is deferred until official developer access exists.

## Ingestion

- mock — development/seed
- fit — user-uploaded FIT files (Phase 7)
- strava — official Strava OAuth (Phase 8)
- garmin — official Connect Developer Program OAuth (deferred; stub only; programme not accepting new apps as of 2026-08)

Garmin data, when live import exists, must come from the official Garmin Connect Developer Program using OAuth 2.0.

The application will **not**:

- scrape Garmin Connect or Strava
- collect or store Garmin or Strava usernames or passwords
- use unofficial Garmin or Strava authentication
- invent Garmin or Strava API endpoints or credentials

Activity pull ingestion is isolated behind a provider interface:

- `MockActivityProvider` for development, tests, and seed data
- `GarminActivityProvider` as a stub until official developer credentials exist. The stub raises; it does not invent HTTP endpoints.
- `StravaActivityProvider` maps official Strava JSON to `ProviderActivity`. HTTP uses documented `strava.com` OAuth and API v3 URLs only.

FIT import is a push path (`app/integrations/fit/` + `app/services/fit_import.py`), not a pull provider. The same user may have `fit`, `mock`, and `strava` rows. This phase does not merge FIT and Strava copies of the same physical run.

OAuth client secrets live in environment variables. Strava access/refresh tokens are Fernet-encrypted in `strava_connections`. They are never returned by the API, never written to logs, and never included in privacy export. Garmin and Strava env vars may be empty; the app still boots. Connecting Strava requires `ENCRYPTION_KEY`. Losing `ENCRYPTION_KEY` or the database means friends must reconnect Strava.

## Security baseline already in place

- Secrets are environment variables; `.env` is gitignored; `.env.example` has placeholders only
- CORS is restricted to `FRONTEND_URL`
- Security headers on API responses
- OpenAPI docs disabled when `ENVIRONMENT=production`
- Production rejects debug mode, placeholder `SECRET_KEY` values, http `FRONTEND_URL`, and empty SMTP
- Database access is async SQLAlchemy (parameterised queries)
- Docker images run as a non-root user (`pacelab`); Caddy is the TLS edge
- Health checks do not expose stack traces, secrets, or mail tokens

Session cookies, CSRF, Argon2id password hashing, and account endpoints are in place as of Phase 2. Privacy export, deletion, cookie-consent UI, and draft legal pages are in place as of Phase 6 and must not be weakened by later Garmin or billing work.

## Multi-user readiness

Every table that stores personal running data has an explicit `user_id` ownership column (`ON DELETE CASCADE`). API handlers take the current user from the authenticated session, never from a client-supplied `user_id`. Activity rows are unique per `(user_id, provider, provider_activity_id)` so two accounts can import the same mock ids without colliding, and a repeated sync cannot duplicate a run.
