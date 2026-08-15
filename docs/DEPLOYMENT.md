# Coolify deployment

Use the Dockerfile build pack with base directory `/`, Dockerfile location
`/Dockerfile`, and exposed port `8000`. Coolify should send traffic to the
container port; the application starts Daphne on `0.0.0.0:${PORT:-8000}`.

Configure runtime variables in Coolify rather than committing an `.env` file.
For production, `DEBUG` must be `False` and Django requires:

- `DJANGO_SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `CORS_ALLOWED_ORIGINS`
- `DATABASE_URL`
- `AI_SYMPTOMS_URL`
- `AI_VISION_URL`
- `AI_FUSION_URL`

Redis can be configured with `REDIS_URL`, or the existing `REDIS_HOST` and
`REDIS_PORT` pair. A Celery worker is deployed separately with:

```
celery -A medismile worker --loglevel=INFO
```

Set `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` when they differ from the
Redis URL. The web container does not start a Celery worker.

For a single Coolify web instance, the entrypoint runs migrations and static
collection by default. Set `RUN_MIGRATIONS=false` or `COLLECT_STATIC=false`
only when those operations are performed separately.

Attach persistent storage to `/app/media`. If local backups are enabled, also
attach persistent storage to `/app/backups`; local backups do not replace an
off-site backup policy.

The container health check is TCP-level on `127.0.0.1:${PORT:-8000}` and does
not call AI services, Redis, or PostgreSQL.
