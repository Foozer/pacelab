# Deploy PaceLab (friend-scale)

This is the operator runbook for putting PaceLab on the public internet for you and a handful of friends. It is a **private beta**, not a SaaS launch.

The agent cannot buy a domain, create a VPS, or register SMTP/Strava apps. Those steps are yours. The repo provides production Compose, Caddy TLS, SMTP sending, and this checklist.

Recommended default: **one VPS (Hetzner or DigitalOcean) + Docker Compose + Caddy (Let’s Encrypt) + daily `pg_dump` copied off the box**. Mail via **Resend SMTP** (or Postmark / Amazon SES SMTP). Do not use Kubernetes.

Local development is unchanged: `docker compose up --build` on your laptop (`http://localhost:5173`). Do not point friends at localhost.

---

## What friends get

- One public origin: `https://<your-domain>`
- Register / sign in (email confirmation is **not** required to sign in)
- Real verification and password-reset mail
- FIT upload and official Strava connect + sync
- No “sync sample runs”, no Account-page development outbox, no mock seed

Rate limiting is **in-process in one API worker**. That is the documented friend-scale default. Do not run multiple backend replicas until you add a shared rate-limit store (see “When you outgrow one VPS”).

---

## Human checklist (in order)

### 1. Domain

1. Buy or reuse a domain (any registrar).
2. You will point it at the VPS in step 3. Typical records:
   - `A` (and `AAAA` if you have IPv6) for `@` / apex → VPS
   - Optional `www`: the default `deploy/Caddyfile` serves the apex only. Add a `www` record and a Caddy `redir` only if you want `www`.
3. MX is **not** required if you send mail through a transactional provider’s SMTP.
4. After the mail provider is set up, add **SPF / DKIM / DMARC** exactly as that provider shows (not invented here).

Replace `<your-domain>` everywhere below with the hostname friends will type (no `https://`).

### 2. VPS

1. Create a small Ubuntu VPS (2 GB RAM is enough for friends).
2. SSH keys only; disable password SSH if the host allows it.
3. Firewall: **22** (your IP if you can), **80**, **443**. Do **not** publish PostgreSQL (`5432`) to the world.
4. Install Docker Engine + Docker Compose plugin.
5. Clone this repository (or copy a release) to e.g. `/opt/pacelab`.

### 3. DNS

Once you have the VPS public IPv4 (and IPv6):

- `A` `<your-domain>` → that IPv4
- `AAAA` if you use IPv6

Wait until `dig <your-domain>` shows the VPS before requesting TLS (Caddy talks to Let’s Encrypt).

### 4. Secrets (never commit, never reuse laptop `.env`)

On the VPS, `cp .env.example .env` and set at least:

| Variable | Production value |
| --- | --- |
| `ENVIRONMENT` | `production` (Compose also forces this for the API) |
| `DEBUG` | `false` |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` — required to Connect Strava. **If you lose this key, friends must reconnect Strava.** Rotating it without a re-encrypt path has the same effect. |
| `FRONTEND_URL` | `https://<your-domain>` |
| `ALLOWED_HOSTS` | `<your-domain>` (loopback is added automatically for Docker healthchecks) |
| `FORWARDED_ALLOW_IPS` | `*` (only Caddy can reach the API on the Docker network) |
| `POSTGRES_PASSWORD` | long random; **avoid `@ : / #`** so `DATABASE_URL` stays valid, or URL-encode |
| `SMTP_*` | see Email below |
| `STRAVA_*` | see Strava below |
| `PACELAB_DOMAIN` | `<your-domain>` (no scheme) |
| `CADDY_ACME_EMAIL` | your email for Let’s Encrypt notices (not necessarily `SMTP_FROM`) |

Compose sets `DATABASE_URL` inside the backend container to the `postgres` hostname. You do not publish Postgres.

### 5. Email (SMTP)

Create a **transactional** account (Resend, Postmark, or Amazon SES). Verify the sending domain. Copy SMTP credentials — not a personal Gmail password.

**Resend (default recommendation):**

- `SMTP_HOST=smtp.resend.com`
- `SMTP_PORT=465` (implicit TLS) or `587` (STARTTLS)
- `SMTP_USERNAME=resend`
- `SMTP_PASSWORD=` your Resend API key
- `SMTP_FROM=PaceLab <noreply@<your-domain>>` (must be a verified domain/sender)

Production **fails to boot** if SMTP host/from/user/password are empty. Development with empty SMTP still uses the recording outbox.

Never put real passwords in git or in this file. PaceLab does not log recipients in full, tokens, or mail bodies.

### 6. Strava API application

At [Strava API settings](https://www.strava.com/settings/api):

| Field | Value |
| --- | --- |
| Website | `https://<your-domain>` |
| Authorization Callback Domain | `<your-domain>` (host only, no `https://`, no path) |
| Redirect URI (env) | `STRAVA_REDIRECT_URI=https://<your-domain>/api/v1/strava/callback` |

Friends connecting besides the app owner may need **athlete capacity** raised. Strava’s 2026 programme documents a self-upgrade toward 10 athletes. Single-player mode only authenticates the app owner.

Scope stays `activity:read_all`. Do not request `activity:write`. Webhooks are not required for friends who click Sync.

### 7. Start the stack

From the clone on the VPS:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Caddy obtains certificates automatically. Backend runs `alembic upgrade head` on start, then **one** uvicorn worker (no `--reload`, no source bind-mounts).

### 8. After go-live

1. Open `https://<your-domain>/health` — `status` should be `ok`, `environment` should be `production`.
2. Register a **second** test account (not only yours).
3. Request a password reset and complete it from a real inbox.
4. Connect Strava and Sync.
5. Upload a small FIT file.
6. Confirm Settings → Account has **no** “Development mailbox”.
7. Confirm Activities has **no** “Sync sample runs”.

Invite a friend only after those checks pass.

---

## Compose shape

`docker-compose.yml` — laptop development (Vite `--reload`, published `5173`/`8000`/`5432`).

`docker-compose.prod.yml` — VPS:

- **Caddy** publishes 80/443; terminates TLS; routes `/health` and `/api/*` to the API and everything else to the SPA
- **frontend** production image (nginx on 8080, not published)
- **backend** production image (`USER pacelab`, uvicorn, no `--reload`)
- **postgres** volume on the VPS, not published

Friends’ browsers never call Docker DNS names. `VITE_API_BASE_URL` is empty at frontend build time so the app uses same-origin `/api`.

Optional `www`: add DNS and a Caddy site block that `redir`s to the apex. Do not leave the API on a second public hostname.

Rollback: keep the previous git revision; `docker compose -f docker-compose.prod.yml down` then check out the last known-good commit and `up -d --build`. Postgres data stays in the volume unless you delete it. Application rollback does not undo a bad migration — restore from backup if you need the previous schema.

---

## Backups and restore

Encrypted Strava tokens live in Postgres. Losing the disk **or** `ENCRYPTION_KEY` means reconnecting Strava (history already imported stays if the DB is intact).

**Backup** (on the VPS, from the repo root):

```bash
chmod +x scripts/backup-postgres.sh
./scripts/backup-postgres.sh > "pacelab-$(date -u +%Y%m%dT%H%M%SZ).sql"
```

Copy that file **off the box** (another machine, object storage, etc.). Daily is enough for friends.

**Restore** (destroys the current database):

```bash
docker compose -f docker-compose.prod.yml stop backend
chmod +x scripts/restore-postgres.sh
./scripts/restore-postgres.sh pacelab-YYYYMMDDTHHMMSSZ.sql
docker compose -f docker-compose.prod.yml start backend
```

Test this once with a throwaway dump before you invite people. Managed Postgres is the first scale-up if you do not want friend data on one disk (see below).

---

## When you outgrow one VPS

Documented only. Do not build this until you have a measured reason.

| Pressure | First move |
| --- | --- |
| Disk / “I deleted the VPS” | Managed Postgres + automated backups; keep `ENCRYPTION_KEY` in a secret manager |
| More than one API replica | Shared rate-limit store (Redis); sticky sessions not required (sessions are in Postgres) |
| Strava 429 / polling | Webhooks + public callback (Strava docs); still no GPS |
| Large FIT uploads / static | Object storage or CDN for the SPA only; activity bytes still must not be stored |
| Many concurrent users | Extra uvicorn workers **or** a second small API box behind the same proxy; measure `/health` and DB CPU first |
| Multi-region / compliance | Far later. Do not claim GDPR/CCPA certification |

Honest default: this VPS + Caddy + Compose + daily off-box `pg_dump` will serve tens of friends. Kubernetes is not the next step after “my running club wants accounts”.

---

## Honesty / what this is not

- Private beta / friends test, not “PaceLab is generally available”
- Connecting Strava is connected to Strava, not Garmin
- PaceLab is not a Strava or Garmin partner
- Legal pages remain drafts
- No Google Analytics or other trackers
- Seed (`python -m app.db.seed`) still refuses in production
