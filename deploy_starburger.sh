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
git reset --hard origin/"$BRANCH"
git clean -fd  

echo "Код обновлён до версии $(git rev-parse --short HEAD)"

echo "2. Установка/обновление Node.js библиотек..."
npm ci

echo "3. Пересборка JS-кода (Parcel)..."
npm run build

echo "4. Установка/обновление Python-библиотек..."
source venv/bin/activate
pip install --break-system-packages -r requirements.txt
deactivate

echo "5. Применение миграций и сбор статики..."
source venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput 
deactivate

echo "6. Перезапуск основных сервисов..."
sudo systemctl restart gunicorn
sudo systemctl reload nginx

echo "7. Уведомление Rollbar о деплое..."

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$ROLLBAR_TOKEN" ]; then
    echo "   Предупреждение: ROLLBAR_TOKEN не найден в .env — уведомление пропущено."
else
    COMMIT_HASH=$(git rev-parse HEAD)
    SHORT_HASH=$(git rev-parse --short HEAD)

    RESPONSE=$(curl -s -X POST "https://api.rollbar.com/api/1/deploy" \
        -F "access_token=$ROLLBAR_TOKEN" \
        -F "environment=production" \
        -F "revision=$COMMIT_HASH" \
        -F "local_username=burger_deploy")

    echo "   $RESPONSE"
fi

echo "========================================"
echo "       Деплой успешно завершён!"
echo "========================================"