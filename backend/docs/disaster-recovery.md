# Disaster Recovery

Playbook for recovering the AI Call Agent platform after data loss, a bad
release, or a compromised secret. Run drills for each procedure against a
staging environment before you need them in production.

---

## 0. Golden rules

- PostgreSQL is the **source of truth** for application data. Media files
  (knowledge documents, logos) live separately and must be backed up too.
- Backups are only as good as their restore tests — verify restore
  periodically.
- Keep one backup offsite (different physical location) and confirm the
  stack can boot from a restore before cutting over.

Recommended cadence:

| Artifact           | Cadence        | Retention          |
| ------------------ | -------------- | ------------------ |
| PostgreSQL dump    | daily + pre-migration | 14 days / monthly kept |
| Media files        | daily (rsync/tar)     | 14 days           |
| `.env.production`  | immutable, 1 copy     | forever (secret manager preferred) |

---

## 1. Database backup

Both formats are safe; use `-Fc` (custom) for compressed, restorable dumps.

```bash
BACKUP=$(date +%Y%m%d-%H%M%S)
mkdir -p backups
docker compose -f docker-compose.production.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d callagent -Fc \
  > backups/callagent_${BACKUP}.dump
# optional plain-text copy of the schema for quick inspection
docker compose -f docker-compose.production.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d callagent --schema-only \
  > backups/callagent_schema_${BACKUP}.sql
```

Automate with cron/systemd and copy to offsite storage (S3/R2/gsutil/…).

## 2. Database restore

```bash
docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -d callagent -c "DROP DATABASE callagent;"
docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE callagent OWNER $POSTGRES_USER;"
docker compose -f docker-compose.production.yml exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d callagent --no-owner --no-privileges \
  < backups/callagent_YYYYMMDD-HHMMSS.dump
```

Then restart the app and verify:

```bash
docker compose -f docker-compose.production.yml exec web python manage.py migrate
docker compose -f docker-compose.production.yml exec web python manage.py deployment_check
curl -f https://yourdomain/ready
```

> Restoring over a live database is destructive. Prefer restoring into a fresh
> database (`callagent_restore`), verifying, then renaming.

## 3. Media backup

Knowledge documents, uploads and CMS media live in the `media_volume`:

```bash
docker run --rm \
  -v callagent_media_volume:/data:ro \
  -v "$PWD/backups":/backup \
  alpine tar czf /backup/media_$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

Restore:

```bash
docker run --rm \
  -v callagent_media_volume:/data \
  -v "$PWD/backups":/backup \
  alpine tar xzf /backup/media_YYYYMMDD-HHMMSS.tar.gz -C /data
```

If media files are lost entirely but the database is intact, affected
knowledge documents must be re-uploaded (their metadata/embeddings survive).

## 4. Application rollback

```bash
# 1. Determine the previous good image/tag.
git log --oneline -5
# 2. Rebuild with the previous commit's code (or pull a tagged image).
git checkout <previous-tag-or-commit>
docker compose -f docker-compose.production.yml build web worker
docker compose -f docker-compose.production.yml up -d web worker nginx
# 3. Only roll the schema back if the forward migration actively broke the DB:
docker compose -f docker-compose.production.yml exec web \
  python manage.py migrate <app> <previous-revision>
```

Prefer shipping a forward-fix over rolling schema back. Rolling back a schema
migration does not recover the data that the forward migration transformed.

## 5. Secret rotation

Rotating a secret must not require a restart of dependent clients beyond the
app itself.

### Django / JWT secret keys

```bash
# generate replacements
openssl rand -hex 48
# update backend/.env.production, then recreate web + worker
docker compose -f docker-compose.production.yml up -d --force-recreate web worker
```

Existing JWTs signed with the old key are invalidated — users re-login. Time
the rotation for maintenance windows.

### Twilio / Telnyx

1. Generate new credentials in the provider console.
2. Update `.env.production`.
3. `docker compose ... up -d --force-recreate web worker`.
4. Verify `/telephony/status` reports `connected: true`.
5. Revoke the old credential only after confirming inbound/outbound calls work.

### Database password

1. `ALTER USER ... PASSWORD` in Postgres.
2. Update `POSTGRES_PASSWORD` and `DATABASE_URL` in `.env.production`.
3. Recreate `web` and `worker`.

### LLM / embeddings / STT / TTS keys

Update `.env.production` and recreate the app containers. Keys are read at
startup; no database change is needed.

## 6. Full recovery drill (restore to a blank stack)

```bash
# on a fresh host
git clone <repo> && cd ai-call-agent
cp backend/.env.production.example backend/.env.production   # same values as prod
docker compose -f docker-compose.production.yml up -d postgres redis
# wait for healthy, then restore as in section 2, then:
docker compose -f docker-compose.production.yml up -d --build
docker compose -f docker-compose.production.yml exec web python manage.py migrate
docker compose -f docker-compose.production.yml exec web python manage.py collectstatic --noinput
curl -f https://yourdomain/ready
```

## 7. Alerting

Alert on failed backups and failed readiness checks:

- cron job exits non-zero when `pg_dump` fails → page an operator
- monitor `/ready` (200 expected) every 30s
- watch `worker` container restarts for stuck Celery tasks