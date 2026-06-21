#!/bin/bash

set -e

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting Starburger entrypoint..."

echo "Waiting for frontend build..."
while [ ! -d /app/www/starburger/bundles ] || [ -z "$(ls -A /app/www/starburger/bundles 2>/dev/null)" ]; do
    echo "Waiting for frontend files..."
    sleep 2
done

log "Frontend files:"
ls -la /app/www/starburger/bundles/ | head -10

echo "Running as user: $(whoami)"

log "Starting Gunicorn server..."

WORKERS="${GUNICORN_WORKERS:-3}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

log "Workers: $WORKERS, Timeout: $TIMEOUT"

exec gunicorn \
    --workers $WORKERS \
    --bind 0.0.0.0:8000 \
    --timeout $TIMEOUT \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    star_burger.wsgi:application