#!/bin/bash
set -e

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting Starburger entrypoint..."

# Проверка SECRET_KEY
if [ -z "$SECRET_KEY" ]; then
    log "ERROR: SECRET_KEY not set!"
    exit 1
fi

# Проверка DEBUG
if [ "$DEBUG" = "True" ]; then
    log "WARNING: DEBUG is True in production!"
fi

# Ожидание базы данных
log "Waiting for database..."
MAX_RETRIES=30
RETRY_COUNT=0
until pg_isready -h postgres -U ${POSTGRES_USER} -d ${POSTGRES_NAME} 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        log "ERROR: Database not ready after ${MAX_RETRIES} attempts"
        exit 1
    fi
    log "Waiting for database... (${RETRY_COUNT}/${MAX_RETRIES})"
    sleep 2
done
log "Database is ready!"

# Ожидание фронтенда
log "Waiting for frontend build..."
MAX_WAIT=120
WAITED=0
while [ ! -d /app/www/starburger/bundles ] || [ -z "$(ls -A /app/www/starburger/bundles 2>/dev/null)" ]; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        log "ERROR: Frontend files not found after ${MAX_WAIT}s"
        exit 1
    fi
    log "Waiting for frontend files... (${WAITED}s)"
    sleep 2
    WAITED=$((WAITED + 2))
done

log "Frontend files found:"
ls -la /app/www/starburger/bundles/ | head -10

log "Running as user: $(whoami)"
log "Current directory: $(pwd)"
log "Files in current directory:"
ls -la

# Создание папок для статики и медиа (если их нет)
mkdir -p staticfiles
mkdir -p media

# Проверка доступа к папкам
if [ -w staticfiles ]; then
    log "✓ staticfiles directory is writable"
else
    log "✗ staticfiles directory is NOT writable!"
    ls -la staticfiles
    exit 1
fi

if [ -w media ]; then
    log "✓ media directory is writable"
else
    log "✗ media directory is NOT writable!"
    ls -la media
    exit 1
fi

# Миграции
log "Running migrations..."
if python manage.py migrate --noinput; then
    log "✓ Migrations completed successfully"
else
    log "✗ Migrations failed!"
    exit 1
fi

# Сбор статики
log "Collecting static files..."
if python manage.py collectstatic --noinput --clear; then
    log "✓ Static files collected successfully"
else
    log "✗ Static files collection failed!"
    exit 1
fi

log "Starting Gunicorn server..."

WORKERS="${GUNICORN_WORKERS:-3}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"
PORT="${PORT:-8000}"

log "Workers: $WORKERS, Timeout: $TIMEOUT, Port: $PORT"

exec gunicorn \
    --workers $WORKERS \
    --bind 0.0.0.0:$PORT \
    --timeout $TIMEOUT \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    star_burger.wsgi:application