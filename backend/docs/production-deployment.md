# Production Deployment

This document describes how to deploy AI Call Agent to a server that will
serve real businesses. It targets the single-host Docker stack in
`docker-compose.production.yml` (nginx → Daphne/Channels → Django, plus
PostgreSQL, Redis and a Celery worker).

Everything in this document is about **infrastructure** — no business logic
changes during deployment.

---

## 1. Architecture

```text
Internet
   │  HTTPS 80/443
   ▼
nginx (TLS + static + React SPA)
   │  proxy (HTTP + WebSockets)
   ▼
Daphne (ASGI) — Django + Channels   ─────►  PostgreSQL
   │                                          ▲
   │                                          │
   └──► Celery worker ──► Redis (broker, cache, channels)
```

One host, one Docker network. Only nginx exposes ports. PostgreSQL and Redis
are internal.

| Service  | Image                    | Role                                                       |
| -------- | ------------------------ | ---------------------------------------------------------- |
| nginx    | built from `nginx/`      | TLS, static/media, React SPA, reverse proxy                |
| web      | built from `backend/`    | Daphne serving Django HTTP + Channels WebSockets           |
| worker   | same image as `web`      | Celery background jobs                                     |
| postgres | postgres:17              | source of truth                                            |
| redis    | redis:7-alpine           | channels layer, cache (DRF throttling), Celery broker      |

---

## 2. Prerequisites

- Docker + Docker Compose plugin
- A domain name whose DNS **A record** points at the server (e.g.
  `app.yourbusiness.com`)
- Ports 80 and 443 reachable from the internet
- `ffmpeg` will be installed in the image (required for the streaming voice
  path's MP3 → G.711 conversion)

---

## 3. Environment variables

Copy the template and fill it in:

```bash
cp backend/.env.production.example backend/.env.production
```

All secrets live **only** in this file (git-ignored). Required values:

| Variable | Purpose |
| -------- | ------- |
| `DOMAIN` | nginx `server_name` + certificate path |
| `PUBLIC_BASE_URL` | caller-facing webhook/media URL (**must be `https://…`**) |
| `DJANGO_ENV=production` | forces safe defaults and fails fast on insecure settings |
| `DJANGO_SECRET_KEY` | `openssl rand -hex 48` |
| `JWT_SECRET_KEY` | second independent long random value |
| `POSTGRES_DB/USER/PASSWORD` | PostgreSQL credentials (used by both postgres + Django) |
| `DATABASE_URL` | points at the `postgres` compose service |
| `REDIS_URL` | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | `redis://redis:6379/1` |
| `DJANGO_ALLOWED_HOSTS` | your public hosts |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://yourdomain` |
| `TWILIO_*` / `TELNYX_*` | telephony credentials |
| `LLM_API_KEY`, `STT_*`, `TTS_*`, `EMBEDDING_*` | AI provider keys |

`DJANGO_DEBUG` must be `0`; `DJANGO_ENV=production` refuses to start
otherwise. Never commit `.env.production`.

---

## 4. Startup

```bash
docker compose pull
docker compose -f docker-compose.production.yml up -d --build
docker compose -f docker-compose.production.yml ps
```

The `web` entrypoint automatically runs:

- `python manage.py migrate --noinput`
- `python manage.py collectstatic --noinput`

Into the shared `static_volume`, which nginx serves read-only.

### Create the first superuser

```bash
docker compose -f docker-compose.production.yml exec web python manage.py createsuperuser
```

Seed the CMS if the database is new:

```bash
docker compose -f docker-compose.production.yml exec web python manage.py seed_cms
```

---

## 5. Verification

```bash
curl -f https://yourdomain/ready
# {"status": "ok", "database": "ok", "redis": "ok"}

curl -f https://yourdomain/db-health
curl -f https://yourdomain/health
curl -f https://yourdomain/widget.js | head
curl -f https://yourdomain/public/config/<deployment-identifier>
```

Run the deployment checklist from the container:

```bash
docker compose -f docker-compose.production.yml exec web python manage.py deployment_check
```

---

## 6. Database

Create/manage the database through PostgreSQL itself; Django never owns
schema management beyond applying migrations.

```bash
# Create a database on the running cluster (rarely needed — compose creates it)
docker compose -f docker-compose.production.yml exec postgres \
  psql -U $POSTGRES_USER -c "CREATE DATABASE callagent OWNER $POSTGRES_USER"
```

### Backups

```bash
BACKUP=$(date +%Y%m%d-%H%M%S)
docker compose -f docker-compose.production.yml exec -T postgres \
  pg_dump -U $POSTGRES_USER -d callagent -Fc \
  > backups/callagent_${BACKUP}.dump
```

Keep a 14-day rotating set, plus one offsite copy per week. See
`disaster-recovery.md` for restore.

---

## 7. Redis

Redis serves three roles: Channels layer, Django cache (DRF throttling), and
the Celery broker. It is optional in development (`REDIS_URL` empty → in-memory
layers), but expected in production — `/ready` fails when `REDIS_URL` is set yet
Redis is unreachable.

```bash
docker compose -f docker-compose.production.yml exec redis redis-cli ping
```

---

## 8. Celery

The worker runs queued background work. Currently only infrastructure health
tasks exist; future work includes call summaries, analytics aggregation,
document processing and notifications.

```bash
docker compose -f docker-compose.production.yml logs -f worker
# quick smoke test of broker/worker plumbing:
docker compose -f docker-compose.production.yml exec worker \
  python -c "from core.tasks import ping; print(ping.delay().get(timeout=10))"
```

`ping.delay()` enqueues; the worker consumes and stores the result on Redis.

---

## 9. Daphne / ASGI

Daphne serves **both** HTTP and WebSockets from one process:

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

- HTTP: all Django (DRF) requests
- WebSocket: `/telephony/twilio/media` (Twilio Media Streams), authenticated by
  the per-call stream token embedded in the URL

WSGI is untouched; `manage.py runserver` and gunicorn-style WSGI deploys still
work.

---

## 10. Nginx + HTTPS

The stack expects certbot certificate paths on the host:

```text
./certs/letsencrypt/live/<DOMAIN>/fullchain.pem
./certs/letsencrypt/live/<DOMAIN>/privkey.pem
```

Obtain them once:

```bash
# install certbot + nginx plugin on the host, then:
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com \
  --cert-path ... --key-path ...
# or mount certbot's live/archive/letsencrypt dirs straight into compose
```

Then place them the compose mounts expect (`./certs/letsencrypt/…`), or adjust
the volume mapping.

Add the ACME challenge placeholder so a webroot renewal works:

```nginx
location /.well-known/acme-challenge/ { root /var/lib/letsencrypt-http; }
```

(already present in `nginx/prod.conf.template`).

Validate the rendered config after any nginx edit:

```bash
docker compose -f docker-compose.production.yml exec nginx nginx -t
docker compose -f docker-compose.production.yml exec nginx nginx -s reload
```

WebSocket paths (`/telephony/…`) use dedicated long proxy timeouts so live
voice streams are never cut off by the proxy; `.html`-less API prefixes
(`/auth`, `/public`, `/widget.js`, …) are proxied to Django, everything else
is the React SPA.

---

## 11. Twilio

After provisioning an inbound/trial Twilio number, set its **Voice** settings
to call our webhooks (`PUBLIC_BASE_URL` must be public HTTPS):

```
A call comes in      → POST https://<PUBLIC_BASE_URL>/telephony/webhook/inbound
Call status changes  → POST https://<PUBLIC_BASE_URL>/telephony/webhook/status
```

Media streams (when `VOICE_STREAMING_ENABLED=1`) use
`wss://<PUBLIC_BASE_URL>/telephony/twilio/media?token=<per-call-token>`.

Signature validation is mandatory: every webhook is verified with the Twilio
auth token against the exact request URL; invalid signatures are rejected.

## 12. Telnyx

Set the connection's Voice API Application webhook to
`https://<PUBLIC_BASE_URL>/telephony/webhook/telnyx`. Events are verified using
`TELNYX_PUBLIC_KEY` (Ed25519) and rejected on mismatch.

---

## 13. Readiness checks

| Endpoint   | Behaviour                                            |
| ---------- | ---------------------------------------------------- |
| `/health`  | liveness – always 200 while the process is up        |
| `/db-health` | database reachability (503 otherwise)              |
| `/ready`   | readiness – database always + Redis when configured (503 otherwise) |

Point your load balancer/monitor at `/ready`.

---

## 14. Logging & monitoring

- Production logs are **structured JSON** (one object per line) with
  `request_id`, level, logger and message; every HTTP response carries
  `X-Request-ID` so you can trace a request end to end.
- Secrets (API keys, auth tokens, Django/JWT secret keys) are redacted from
  log output as defense-in-depth.
- Set `DJANGO_LOG_LEVEL` to control verbosity (`INFO` default, `WARNING` to
  quiet).

---

## 15. Rollback

1. Revert to the previous image: `docker compose ... up -d <old image tag>`
2. Schema rollback is only safe for the immediately previous migration:
   `docker compose ... exec web python manage.py migrate <app> <previous-rev>`
3. Restore data if needed (see `disaster-recovery.md`).

New deployments should always be **forward** migrations; if a deploy fails,
prefer fixing forward over rolling the schema back.

---

## 16. The deployment checklist

`python manage.py deployment_check` verifies, without writing:

- DEBUG off / secret key set / hosts + CSRF origins configured
- database reachability
- all migrations applied
- `collectstatic` dry-run
- security headers configuration

It exits non-zero on critical failures and never prints secrets. Run it in CI
and before every release:
`python manage.py deployment_check --strict`.