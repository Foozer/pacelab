# PaceLab

PaceLab is a running analytics platform. It helps runners understand whether their fitness is actually improving — pace versus heart rate, easy running, volume, consistency, and long-term trends.

This repository is a monorepo. The first user is the developer, but the architecture is intended for a future multi-user SaaS product.

Garmin Connect is **not** scraped. When live import exists, it will use the official Garmin Connect Developer Program and OAuth 2.0. Until those credentials are available, the app runs without Garmin and stores PaceLab accounts independently.

## Current status — Phase 5

Completed:

- Phase 1 foundation (Compose, FastAPI, PostgreSQL, React, health, migrations)
- Phase 2 authentication (sessions, CSRF, Argon2id, account pages)
- Phase 3 activity import (models, mock provider, sync, seed)
- Phase 4 dashboard, activity history, and activity-detail charts
- Aerobic efficiency (pace at a similar heart rate; Improving / Stable / Not enough data)
- Easy Running page with a configurable heart-rate range (default 140–150 bpm)
- Trends page (pace, HR, weekly distance, frequency, comparable pace; 4w–all)
- Simple 5K estimate (Riegel scaling, labelled as an estimate)
- Dashboard cards for 5K estimate, easy pace, and aerobic efficiency

Not in this phase: privacy export/deletion, cookie-consent UI, live Garmin OAuth, or production deploy docs.

## Requirements

- Docker and Docker Compose (intended development path)
- Alternatively: Python 3.12+, Node.js 22+, and PostgreSQL 16 on `localhost:5432`

Enable Docker Desktop **and** WSL integration if `docker` is missing inside WSL:

1. Start Docker Desktop on Windows.
2. Settings → Resources → WSL integration → enable your distro.
3. Use `docker compose` (space), not `docker-compose` (hyphen).

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- App: http://localhost:5173
- Dashboard (after sign-in): http://localhost:5173/
- Easy running: http://localhost:5173/easy-running
- Trends: http://localhost:5173/trends
- Activities: http://localhost:5173/activities
- API health: http://localhost:8000/health
- OpenAPI (development only): http://localhost:8000/docs

The backend runs `alembic upgrade head` on startup.

Create an account at http://localhost:5173/register (password at least 10 characters), or use the seed user below.

### After changing dependencies

The backend image installs Python packages at build time, so a new entry in `backend/pyproject.toml` needs a rebuild. Skipping it leaves the container importing an older dependency set and the healthcheck reports `unhealthy`:

```bash
docker compose up -d --build backend
```

The frontend keeps `node_modules` in a named volume that survives rebuilds, so its container runs `npm install` on start to pick up new packages. Recreate the volume with `docker volume rm pacelab_frontend_node_modules` if it ever gets into a bad state.

Run either the Compose stack or the local dev servers, not both. They bind the same ports (8000, 5173) and use different databases, so a mixed setup silently serves one stack while you inspect the other.

### Local (no Docker)

```bash
cp .env.example .env
# PostgreSQL must be reachable at DATABASE_URL
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# in another terminal
cd frontend && npm install && npm run dev
```

### Seed mock activities (development only)

Creates `dev@example.com` if needed and imports the mock catalog. Refuses to run when `ENVIRONMENT=production`. Does not write Garmin credentials.

Default password: `pacelab-dev-local-only` (override with `PACELAB_SEED_PASSWORD`).

```bash
# Docker
docker compose exec backend python -m app.db.seed

# Local, from backend/
.venv/bin/python -m app.db.seed
```

Then sign in at http://localhost:5173/login. The home page is the dashboard. Re-running seed updates existing mock rows instead of duplicating them.

## Tests

PostgreSQL must be running. Tests apply migrations and truncate account and activity tables after each async API test.

With Docker:

```bash
docker compose up -d postgres
docker compose run --rm backend pytest
```

Locally:

```bash
cd backend && source .venv/bin/activate && pytest
```

Do not run pytest inside the already-running backend container: it truncates that database and wipes seeded data.

## Lint and type checks

```bash
docker compose run --rm backend ruff check app tests
docker compose run --rm backend mypy app
docker compose run --rm frontend npm run lint
docker compose run --rm frontend npm run typecheck
```

## Configuration

See [docs/configuration.md](docs/configuration.md) for every environment variable.

See [docs/architecture.md](docs/architecture.md) for Garmin, security, and multi-user constraints.

`ACTIVITY_PROVIDER` defaults to `mock`. Setting it to `garmin` selects the stub, which returns `501` until official OAuth exists.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness/readiness: process up and PostgreSQL reachable |
| `GET` | `/api/v1/auth/csrf` | Issue CSRF cookie and token |
| `POST` | `/api/v1/auth/register` | Create account and start a session |
| `POST` | `/api/v1/auth/login` | Sign in |
| `POST` | `/api/v1/auth/logout` | Revoke session |
| `POST` | `/api/v1/auth/email/verify` | Confirm email with a one-time token |
| `POST` | `/api/v1/auth/email/resend` | Queue another confirmation email |
| `POST` | `/api/v1/auth/password-reset/request` | Queue a reset email (same response whether the account exists) |
| `POST` | `/api/v1/auth/password-reset/confirm` | Set a new password from a reset token |
| `GET` | `/api/v1/users/me` | Current authenticated user |
| `POST` | `/api/v1/users/me/password` | Change password |
| `GET` | `/api/v1/dashboard` | Last-7-day volume, recent runs, pace/HR trend, 5K estimate, easy pace, aerobic efficiency |
| `GET` | `/api/v1/analytics/easy-running` | Easy-range aggregates and pace trend (`hr_min`, `hr_max`) |
| `GET` | `/api/v1/analytics/trends` | Trend series (`range` = 4w/8w/3m/6m/1y/all, plus HR band) |
| `GET` | `/api/v1/analytics/aerobic-efficiency` | Efficiency direction and score over easy/moderate runs |
| `GET` | `/api/v1/activities` | Paginated activity list (`limit`, `offset`, `from_date`, `to_date`, `activity_type`) |
| `GET` | `/api/v1/activities/{id}` | One activity (404 if missing or owned by someone else) |
| `POST` | `/api/v1/activities` | Create an activity for the current user |
| `POST` | `/api/v1/activities/sync` | Import from the configured provider (mock by default) |

Mutating `/api` routes require the CSRF cookie plus `X-CSRF-Token`. Session identity is taken from the `pacelab_session` cookie, never from a client-supplied `user_id`.

Successful health payload:

```json
{
  "status": "ok",
  "database": "connected",
  "version": "0.1.0",
  "environment": "development"
}
```

If the database is down the API returns `503` with `"status": "unhealthy"`. Errors otherwise use:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Not Found"
  }
}
```

## Known limitations (Phase 5)

- No SMTP provider: verification and password-reset emails are recorded in memory. In `ENVIRONMENT=development` they appear on the account page. Tokens are never written to logs.
- Email confirmation is not required to sign in.
- Rate limiting is in-process only (one API worker). A shared store can replace it later.
- Aerobic efficiency and the 5K figure are application estimates, not lab or race results.
- The default easy heart-rate band is 140–150 bpm and is a query parameter (also stored in the browser if you change it). It is not a personal Zone 2 and is not saved in PostgreSQL.
- Activity samples omit GPS. That is intentional until there is a product need.
- Date filters are UTC calendar days, not the browser’s local timezone. Weekly trend buckets are Monday-based UTC weeks.
- Privacy export/deletion, cookie-consent UI, and legal pages are later phases.
- `GarminActivityProvider` is a stub: it does not call Garmin and must not be given invented endpoints.
- Production deployment runbooks land in a later phase.
