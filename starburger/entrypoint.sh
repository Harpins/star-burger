#!/bin/bash
# entrypoint.sh - запуск через Gunicorn

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

log "Waiting for PostgreSQL to be ready..."
while ! python -c "
import os, time, psycopg2
from urllib.parse import urlparse
db_url = os.getenv('DATABASE_URL') or f'postgresql://{os.getenv('POSTGRES_USER','')}:{os.getenv('POSTGRES_PASSWORD','')}@{os.getenv('POSTGRES_HOST','postgres')}:5432/{os.getenv('POSTGRES_DB','')}' 
parsed = urlparse(db_url)
try:
    conn = psycopg2.connect(
        host=parsed.hostname or 'postgres',
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        dbname=parsed.path.lstrip('/')
    )
    conn.close()
    print('Database is ready!')
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; do
    log "Postgres is not ready yet... waiting 2 seconds"
    sleep 2
done

log "PostgreSQL is ready ✓"


log "Running migrations..."
python manage.py migrate --noinput

log "Collecting static..."
python manage.py collectstatic --noinput
log "Static files collected successfully"

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