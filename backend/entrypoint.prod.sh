#!/bin/sh
# Production entrypoint: migrate, collect static files, then exec the command.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"