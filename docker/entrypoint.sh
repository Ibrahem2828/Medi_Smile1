#!/bin/sh
set -eu

if [ "${COLLECT_STATIC:-true}" = "true" ]; then
    python manage.py collectstatic --noinput
fi

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

exec daphne -b 0.0.0.0 -p "${PORT:-8000}" medismile.asgi:application
