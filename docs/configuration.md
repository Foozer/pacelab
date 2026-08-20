# Configuration reference

Copy `.env.example` to `.env` before starting Docker Compose. Never commit `.env`. Production on a VPS uses the same file with different values; see [docs/deploy.md](deploy.md).

| Variable | Required | Description |
| --- | --- | --- |
| `ENVIRONMENT` | yes | `development`, `production`, or `test`. Production disables OpenAPI and rejects unsafe settings. |
| `DEBUG` | yes | Verbose application/SQL output. Must be `false` in production. |
| `APP_VERSION` | no | Version string returned by `GET /health`. Defaults to `0.1.0`. |
| `LOG_LEVEL` | no | `DEBUG`, `INFO`, `WARNING`, or `ERROR`. Production logs JSON to stdout. |
| `SECRET_KEY` | yes | Signing secret reserved for future signed values. Use a long random value in any deployed environment. Session cookies use unguessable tokens hashed at rest rather than this key. |
| `ENCRYPTION_KEY` | to connect Strava | Fernet key for encrypting Strava OAuth tokens at rest. Not required to boot. Required to connect Strava. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Reserved later for Garmin tokens too. |
| `ALLOWED_HOSTS` | production | Comma-separated hostnames for `TrustedHostMiddleware` (e.g. `pacelab.health`). `127.0.0.1` and `localhost` are always appended so the Compose healthcheck can succeed. |
| `FRONTEND_URL` | yes | Browser origin allowed by CORS. Do not use `*`. `localhost` and `127.0.0.1` are both accepted. Production must be `https://<domain>`. |
| `VITE_API_BASE_URL` | no | Absolute API URL as seen by the browser. Leave empty in development and in production Compose so the browser uses same-origin `/api` (Vite proxy locally, Caddy in production). |
| `VITE_API_PROXY_TARGET` | frontend dev | Backend URL used by the Vite dev-server proxy (`http://127.0.0.1:8000` locally, `http://backend:8000` in Compose). |
| `POSTGRES_USER` | yes | PostgreSQL role. |
| `POSTGRES_PASSWORD` | yes | PostgreSQL password. Dev placeholder only in `.env.example`. |
| `POSTGRES_DB` | yes | PostgreSQL database name. |
| `POSTGRES_PORT` | no | Host port mapped to Postgres in **development** Compose (default `5432`). Not published in production. |
| `DATABASE_URL` | yes | SQLAlchemy URL. Must use `postgresql+asyncpg://`. Compose overrides the host to `postgres` inside the backend container. |
| `FORWARDED_ALLOW_IPS` | production | IPs allowed to set `X-Forwarded-*` (uvicorn `--forwarded-allow-ips`). Production Compose default `*` because only Caddy can reach the API. |
| `SMTP_HOST` | production | SMTP hostname. Empty in development → recording sender / Account outbox. Required in production (fail closed). |
| `SMTP_PORT` | production | `587` (STARTTLS) or `465` (implicit TLS). |
| `SMTP_USERNAME` | production | SMTP username (e.g. `resend`). Required in production. |
| `SMTP_PASSWORD` | production | SMTP password or API key. Never commit. Never logged. Required in production. |
| `SMTP_FROM` | production | `From` header, e.g. `PaceLab <noreply@example.com>`. Required in production. |
| `PACELAB_DOMAIN` | production Compose | Public hostname for Caddy (no scheme). Not read by FastAPI. |
| `CADDY_ACME_EMAIL` | production Compose | Let’s Encrypt account email for Caddy. |
| `GARMIN_CLIENT_ID` | deferred | Official Garmin Connect Developer Program client id. Unused. Programme not accepting new apps as of 2026-08. |
| `GARMIN_CLIENT_SECRET` | deferred | Official Garmin client secret. Unused. Never log or commit this value. |
| `GARMIN_REDIRECT_URI` | deferred | OAuth redirect URI registered with Garmin. Unused. |
| `STRAVA_CLIENT_ID` | to connect Strava | Official Strava OAuth client id from https://www.strava.com/settings/api . Not required to boot. |
| `STRAVA_CLIENT_SECRET` | to connect Strava | Official Strava client secret. Never log or commit this value. |
| `STRAVA_REDIRECT_URI` | to connect Strava | Must match the callback registered with Strava. Local: `http://localhost:8000/api/v1/strava/callback`. Production: `https://<domain>/api/v1/strava/callback`. |
| `ACTIVITY_PROVIDER` | no | `mock` (default) or `garmin`. Garmin is a stub (deferred OAuth) and will not call invented endpoints. FIT import is a separate upload route. |
| `PACELAB_SEED_EMAIL` | seed | Optional email for `python -m app.db.seed`. Defaults to `dev@example.com`. Must be an address `EmailStr` accepts, so reserved suffixes such as `.local` will not work. |
| `PACELAB_SEED_PASSWORD` | seed | Optional password for the seed user. Defaults to the documented local-only value in the README. Never use this in production. |

Cookies:

- `pacelab_session` — HttpOnly, SameSite=Lax, `Secure` when `ENVIRONMENT=production` or `FRONTEND_URL` is https. Holds the raw session token.
- `pacelab_csrf` — readable by JavaScript, SameSite=Lax, same Secure rule. Send the value as `X-CSRF-Token` on POST/PUT/PATCH/DELETE to `/api/*`.

Fetch `GET /api/v1/auth/csrf` before the first mutating request.

Heart-rate ranges for Easy Running, Trends, and the dashboard easy-pace card are not environment variables. They are API query parameters (`hr_min`, `hr_max`; default 140–150 bpm) and may be remembered in the browser. They are not stored in PostgreSQL.

## Docker vs host URLs

- Browser and host tools (pytest on the host, `curl`) talk to `localhost`.
- The backend container talks to Postgres at hostname `postgres`.
- In development the browser calls Vite (`/health`, `/api`); Vite proxies those paths to the backend. Do not point the browser at the Compose service name `backend`.
- In production the browser calls `https://<domain>`; Caddy proxies `/health` and `/api` to the backend and the rest to the SPA.
