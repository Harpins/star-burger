#!/bin/bash
# entrypoint.sh - Минимальная версия

set -e

echo "Waiting for frontend build..."
while [ ! -d /app/www/starburger/bundles ] || [ -z "$(ls -A /app/www/starburger/bundles 2>/dev/null)" ]; do
    echo "Waiting for frontend files..."
    sleep 2
done

echo "Frontend found! Starting Django..."

python manage.py migrate --noinput

python manage.py collectstatic --noinput

exec python manage.py runserver 0.0.0.0:8000