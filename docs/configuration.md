# Configuration reference

Copy `.env.example` to `.env` before starting Docker Compose. Never commit `.env`.

| Variable | Required | Description |
| --- | --- | --- |
| `ENVIRONMENT` | yes | `development`, `production`, or `test`. Production disables OpenAPI and rejects unsafe settings. |
| `DEBUG` | yes | Verbose application/SQL output. Must be `false` in production. |
| `APP_VERSION` | no | Version string returned by `GET /health`. Defaults to `0.1.0`. |
| `LOG_LEVEL` | no | `DEBUG`, `INFO`, `WARNING`, or `ERROR`. Production logs JSON to stdout. |
| `SECRET_KEY` | yes | Signing secret reserved for future signed values. Use a long random value in any deployed environment. Session cookies use unguessable tokens hashed at rest rather than this key. |
| `ENCRYPTION_KEY` | no | Reserved for encrypting Garmin OAuth tokens at rest. Leave empty until Phase 7. |
| `ALLOWED_HOSTS` | production | Comma-separated hostnames for `TrustedHostMiddleware`. |
| `FRONTEND_URL` | yes | Browser origin allowed by CORS. Do not use `*`. `localhost` and `127.0.0.1` are both accepted. |
| `VITE_API_BASE_URL` | no | Absolute API URL as seen by the browser. Leave empty in development; the Vite proxy is used instead. |
| `VITE_API_PROXY_TARGET` | frontend dev | Backend URL used by the Vite dev-server proxy (`http://127.0.0.1:8000` locally, `http://backend:8000` in Compose). |
| `POSTGRES_USER` | yes | PostgreSQL role. |
| `POSTGRES_PASSWORD` | yes | PostgreSQL password. Dev placeholder only in `.env.example`. |
| `POSTGRES_DB` | yes | PostgreSQL database name. |
| `POSTGRES_PORT` | no | Host port mapped to Postgres (default `5432`). |
| `DATABASE_URL` | yes | SQLAlchemy URL. Must use `postgresql+asyncpg://`. Compose overrides the host to `postgres` inside the backend container. |
| `FORWARDED_ALLOW_IPS` | production | IPs allowed to set `X-Forwarded-*` when running behind a reverse proxy. |
| `GARMIN_CLIENT_ID` | later | Official Garmin Connect Developer Program client id. Empty until issued. |
| `GARMIN_CLIENT_SECRET` | later | Official Garmin client secret. Never log or commit this value. |
| `GARMIN_REDIRECT_URI` | later | OAuth redirect URI registered with Garmin. |
| `ACTIVITY_PROVIDER` | no | `mock` (default) or `garmin`. Garmin is a stub until Phase 7 and will not call invented endpoints. |
| `PACELAB_SEED_EMAIL` | seed | Optional email for `python -m app.db.seed`. Defaults to `dev@example.com`. Must be an address `EmailStr` accepts, so reserved suffixes such as `.local` will not work. |
| `PACELAB_SEED_PASSWORD` | seed | Optional password for the seed user. Defaults to the documented local-only value in the README. Never use this in production. |

Cookies:

- `pacelab_session` — HttpOnly, SameSite=Lax, `Secure` when `ENVIRONMENT=production` or `FRONTEND_URL` is https. Holds the raw session token.
- `pacelab_csrf` — readable by JavaScript, SameSite=Lax, same Secure rule. Send the value as `X-CSRF-Token` on POST/PUT/PATCH/DELETE to `/api/*`.

Fetch `GET /api/v1/auth/csrf` before the first mutating request.

## Docker vs host URLs

- Browser and host tools (pytest on the host, `curl`) talk to `localhost`.
- The backend container talks to Postgres at hostname `postgres`.
- In development the browser calls Vite (`/health`, `/api`); Vite proxies those paths to the backend. Do not point the browser at the Compose service name `backend`.
