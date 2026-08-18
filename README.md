# PaceLab

PaceLab is a running analytics platform. It helps runners understand whether their fitness is actually improving — pace versus heart rate, easy running, volume, consistency, and long-term trends.

This repository is a monorepo. The first user is the developer, but the architecture is intended for a future multi-user SaaS product.

Garmin Connect is **not** scraped. When live import exists, it will use the official Garmin Connect Developer Program and OAuth 2.0. Until those credentials are available, the app runs without Garmin and stores PaceLab accounts independently.

## Current status — Phase 2

Completed:

- Phase 1 foundation (Compose, FastAPI, PostgreSQL, React, health, migrations)
- `User` model with UUID public identifiers
- Register, login, logout, and current-user APIs
- Argon2id password hashing
- Server-side sessions in HttpOnly, SameSite=Lax cookies (`Secure` in production)
- Double-submit CSRF (`pacelab_csrf` cookie + `X-CSRF-Token`)
- Email verification and password-reset **architecture** (tokens hashed at rest; no SMTP yet)
- Account pages: register, login, settings/account, logout
- Auth tests (registration, login, invalid password, unauthenticated access, user isolation)

Not in this phase: activities, analytics, privacy export/deletion, cookie-consent UI, or live Garmin OAuth.

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
- API health: http://localhost:8000/health
- OpenAPI (development only): http://localhost:8000/docs

The backend runs `alembic upgrade head` on startup.

Create an account at http://localhost:5173/register (password at least 10 characters).

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

## Tests

PostgreSQL must be running. Auth tests apply migrations and truncate account tables after each async test.

With Docker:

```bash
docker compose up -d postgres
docker compose run --rm backend pytest
```

Locally:

```bash
cd backend && source .venv/bin/activate && pytest
```

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

## Known limitations (Phase 2)

- No SMTP provider: verification and password-reset emails are recorded in memory. In `ENVIRONMENT=development` they appear on the account page. Tokens are never written to logs.
- Email confirmation is not required to sign in.
- Rate limiting is in-process only (one API worker). A shared store can replace it later.
- Privacy export/deletion, cookie-consent UI, and legal pages are later phases.
- Garmin provider packages remain import-path stubs until official developer credentials exist.
- Production deployment runbooks land in a later phase.
