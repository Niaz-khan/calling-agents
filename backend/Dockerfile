# Production image for the AI Call Agent backend.
# Used by both the `web` (Daphne/ASGI) and `worker` (Celery) services.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ffmpeg: audio format conversion for the streaming voice path (edge-TTS MP3
# -> G.711 mu-law). libpq5: runtime libs used when psycopg installs free of a
# compiler. curl is a convenience for container healthchecks and debugging.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

ENTRYPOINT ["sh", "/app/entrypoint.prod.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]