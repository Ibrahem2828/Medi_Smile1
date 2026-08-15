# syntax=docker/dockerfile:1.7
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN python -m venv "$VIRTUAL_ENV"

COPY requirements.txt ./
RUN pip install --requirement requirements.txt \
    && pip install "daphne==4.2.2"

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --home-dir /home/app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app . /app

RUN chmod 0555 /app/docker/entrypoint.sh \
    && mkdir -p /app/staticfiles /app/media /app/backups \
    && chown -R app:app /app/staticfiles /app/media /app/backups

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; response = urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health/', timeout=5); assert response.status == 200; response.close()" || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
