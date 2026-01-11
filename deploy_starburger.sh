#!/bin/bash

# deploy_starburger.sh — автоматический деплой star-burger
# Запуск: ./deploy_starburger.sh

set -e

PROJECT_DIR="/var/www/star-burger"
BRANCH="master"

echo "========================================"
echo "  Начинаем деплой star-burger — $(date +'%Y-%m-%d %H:%M:%S')"
echo "========================================"

cd "$PROJECT_DIR"

echo "1. Обновление кода из репозитория ($BRANCH)..."
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "2. Проверка на важные несохранённые изменения"
echo "   (игнорируем staticfiles/ и bundles/)..."

if git diff --quiet -- . ':!staticfiles/' ':!bundles/' && \
   git diff --cached --quiet -- . ':!staticfiles/' ':!bundles/' && \
   [ -z "$(git ls-files --others --exclude-standard | grep -vE '^(staticfiles|bundles)/')" ]; then
    echo "   Репозиторий чист — продолжаем деплой."
else
    echo "ОШИБКА: Обнаружены несохранённые изменения вне staticfiles/ и bundles/"
    git status
    echo "Зафиксируйте или откатите изменения перед деплоем."
    exit 1
fi

echo "3. Установка/обновление Node.js библиотек..."
npm ci

echo "4. Пересборка JS-кода (Parcel) и перезапуск сервиса..."
sudo systemctl restart parcel-watch
npm run build

echo "5. Установка/обновление Python-библиотек..."
source venv/bin/activate
pip install --break-system-packages -r requirements.txt
deactivate

echo "6. Применение миграций Django и сбор static..."
source venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
deactivate

echo "7. Перезапуск сервисов..."
sudo systemctl restart gunicorn
sudo systemctl reload nginx

echo "8. Уведомление Rollbar о деплое..."

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$ROLLBAR_TOKEN" ]; then
    echo "Предупреждение: ROLLBAR_TOKEN не найден — Rollbar пропущен."
else
    COMMIT_HASH=$(git rev-parse HEAD)
    SHORT_HASH=$(git rev-parse --short HEAD)

    RESPONSE=$(curl -s -X POST "https://api.rollbar.com/api/1/deploy" \
        -F "access_token=$ROLLBAR_TOKEN" \
        -F "environment=production" \
        -F "revision=$COMMIT_HASH" \
        -F "local_username=burger_deploy")

    if echo "$RESPONSE" | grep -q '"status":"success"'; then
        echo "Rollbar уведомлён (коммит $SHORT_HASH)"
    else
        echo "Ошибка Rollbar:"
        echo "$RESPONSE"
    fi
fi

echo "========================================"
echo "       Деплой успешно завершён!         "
echo "========================================"