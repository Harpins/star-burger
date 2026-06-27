# Сайт доставки еды Star Burger - Докеризованный

[Рабочая версия сайта, задеплоенного на сервер](https://starburger-derevnin.ru/)
[Админка сайта](https://starburger-derevnin.ru/admin)
[Список заказов (требует логина)](https://starburger-derevnin.ru/manager/orders)


Содержит Django-бэкенд, сборку фронтенда через Parcel, PostgreSQL с Adminer и Nginx + Gunicorn.


Это сайт сети ресторанов Star Burger. Здесь можно заказать превосходные бургеры с доставкой на дом.

![скриншот сайта](https://dvmn.org/filer/canonical/1594651635/686/)


Сеть Star Burger объединяет несколько ресторанов, действующих под единой франшизой. У всех ресторанов одинаковое меню и одинаковые цены. Просто выберите блюдо из меню на сайте и укажите место доставки. Мы сами найдём ближайший к вам ресторан, всё приготовим и привезём.

На сайте есть три независимых интерфейса. Первый — это публичная часть, где можно выбрать блюда из меню, и быстро оформить заказ без регистрации и SMS.

Второй интерфейс предназначен для менеджера. Здесь происходит обработка заказов. Менеджер видит поступившие новые заказы и первым делом созванивается с клиентом, чтобы подтвердить заказ. После оператор выбирает ближайший ресторан и передаёт туда заказ на исполнение. Там всё приготовят и сами доставят еду клиенту.

Третий интерфейс — это админка. Преимущественно им пользуются программисты при разработке сайта. Также сюда заходит менеджер, чтобы обновить меню ресторанов Star Burger.

## Требования

**Docker** 29.0+ и **Docker Compose** 2.20+
- **Git** 
- **4 ГБ RAM** (рекомендуется)
- **Порты 8000, 8080, 80** — должны быть свободны

Docker Compose version v5.0.2

## Запуск сайта локально

1. Скачайте код:
```sh
git clone https://github.com/devmanorg/star-burger.git
```
2. Настройте переменные окружения

Скопируйте файл .env.example в корневую папку и переименуйте в .env

3. Переименуйте папку `nginx.local` в `nginx`. Удалите/переместите файлы, необходимые для деплоя на сервер: `starburger/entrypoint.sh`, `docker-compose.yml`. Манифест `docker-compose.local.yml` переименуйте в `docker-compose.yml`.

### Переменные окружения

- SECRET_KEY=ваш_секретный_ключ_Джанго
- YA_API_KEY= [Токен геокодера](https://developer.tech.yandex.ru/services) 
- ALLOWED_HOSTS=ваши_ip_и_домены [см. документацию Django](https://docs.djangoproject.com/en/5.2/ref/settings/#allowed-hosts)
- DEBUG=False

- ROLLBAR_TOKEN=ваш_rollbar_post_server_item_токен
- ROLLBAR_ENABLED=True

- POSTGRES_NAME=db_name
- POSTGRES_USER=db_user
- POSTGRES_PASSWORD=strong_password
- POSTGRES_PORT=5432
- POSTGRES_HOST=postgres

- CSRF_TRUSTED_ORIGINS=https://ваш_домен1.ru,https://ваш_домен2.ru

- GUNICORN_WORKERS=3
- GUNICORN_TIMEOUT=120


Перейдите в каталог проекта:
```sh
cd star-burger
```

3. Запустите проект

`docker compose up -d --build`


Теперь если зайти на страницу  http://localhost/, то вместо пустой страницы вы увидите:

![](https://dvmn.org/filer/canonical/1594651900/687/)

### Сервисы

Создайте суперпользователя для доступа в админку:

`docker compose exec starburger python manage.py createsuperuser`

Adminer — это легковесный веб-интерфейс для управления базами данных. Он доступен по адресу: **http://localhost:8080**

### Вход в Adminer

1. Откройте в браузере: http://localhost:8080
2. Заполните форму входа:

| Поле | Значение |
|------|----------|
| **Система** | `PostgreSQL` |
| **Сервер** | `postgres` (имя контейнера из docker-compose.yml) |
| **Имя пользователя** | Значение из `.env` → `POSTGRES_USER` |
| **Пароль** | Значение из `.env` → `POSTGRES_PASSWORD` |
| **База данных** | Значение из `.env` → `POSTGRES_NAME` |

3. Нажмите **Войти**



## Production-деплой 

### Подготовка сервера

1. Арендуйте сервер и домен

Сервер должен иметь статический (выделенный) IP‑адрес — он понадобится для настройки домена, SSL‑сертификатов и доступа по SSH.

В качестве примера будет использован домен `yourdomain.ru`

Рекомендуемая конфигурация:

- RAM: 4 GB
- CPU: 4 vCPU
- Диск: 120 GB
- ОС: Ubuntu 24
- Открытые порты: 80, 443, а также 22 для SSH.

2. Подготовьте сервер для работы

- Настройте [доступ по ssh](https://blog.skillfactory.ru/kak-podklyuchitsya-k-serveru-po-ssh/) и создайте [непривилегированного пользователя с sudo правами](https://www.geeksforgeeks.org/linux-unix/how-to-add-user-to-sudoers-in-ubuntu/) для деплоя. Все дальнейшие действия следует проводить из-под нового пользователя.

- Установите Docker и Docker Compose

```bash
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
- Создайте директории для статики и медиа, папку 

```bash
sudo mkdir -p /var/www/starburger/staticfiles
sudo mkdir -p /var/www/starburger/media
sudo chown -R 1000:1000 /var/www/starburger
```

- Установите Nginx и Certbot

```bash
sudo apt update
sudo apt install -y nginx
sudo apt install certbot python3-certbot-nginx
```

- Проверьте статус Nginx, запустите вручную если необходимо и включите автозапуск:

```bash
systemctl status nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

- Проверьте Certbot

```bash
certbot --version
```

- Настройте Nginx

Пример конфига находится в файле `nginx_deploy_example.conf`. Разместите конфигурацию с актуальными данными на сервере.

```bash
sudo nano /etc/nginx/sites-available/starburger
```

- Активируйте конфиг и получите SSL

```bash
sudo ln -s /etc/nginx/sites-available/starburger /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

sudo certbot --nginx -d yourdomain.ru -d www.yourdomain.ru
```

Чтобы проверить работу Nginx и SSL‑сертификата, откройте в браузере ваш домен. На этом этапе допустимо появление ошибки 502 Bad Gateway — она означает, что Nginx активен и корректно обрабатывает HTTPS‑запросы, но не может связаться с бэкенд‑сервисом проекта, т. к. его пока что не развернули на сервере. 

### Разверните проект на сервере

Проект задокеризован, [образы](https://hub.docker.com/repositories/harpins) запушены на `hub.docker.com`

Для деплоя используются два образа:
- `harpins/star-burger-frontend-builder` - одноразовый контейнер для сборки статики
- `harpins/starburger` - основной контейнер

В корневой папке находятся три манифеста:
`docker-compose.deploy.yml` - для развертывания проекта на сервере на основе готовых образов, запушенных на Dockerhub 
`docker-compose.yml` - для локальной сборки контейнеров для деплоя с последующей публикацией на Dockerhub
`docker-compose.local.yml` - используется только для локального запуска сайта - **не нужен при деплое**

Фактическое отличие `docker-compose.yml` и `docker-compose.deploy.yml` заключается лишь в способе задания образа. В первом случае используется `build: ...`, во втором `image: ...`.

1. Разместите на сервере (в одну папку, например, `/opt/starburger/`) файл окружения и содержимое манифеста `docker-compose.deploy.yml` в виде `docker-compose.yml` любым удобным способом.

```bash
nano /opt/starburger/.env
```

```bash
nano /opt/starburger/docker-compose.yml
```

Пример файла с переменными окружения находится в `.env.example`

2. Соберите и запустите контейнеры

```bash
cd /opt/starburger

# Сделать entrypoint.sh исполняемым
chmod +x starburger/entrypoint.sh

# Собрать образы
docker compose build

# Запустить
docker compose up -d

# Проверить работу
docker compose ps
docker compose logs -f starburger
```

3. Настройте админку в джанго, добавьте в БД тестовые данные

Создайте суперпользователя в контейнере

```bash
docker compose exec starburger python manage.py createsuperuser
```

После деплоя БД пустая, из-за чего при попытке внести первые экземпляры `Product` или `Restaurant` через джанго-админку возникает проблема циклической зависимости (например для добавления нового продукта в инлайне требуется выбрать ресторын). Для ее решения можно добавить в БД филлерные данные. Настоящий проект использует PostgreSQL версии 17 в контейнере на базе образа postgres:17-alpine. Внести в нее тестовые данные можно через Django Shell внутри контейнера:

```bash
#Консоль контейнера
docker compose exec starburger bash
```

```bash
#Запуск Shell
python manage.py shell
```

```bash
#Добавление тестового ресторана
from foodcartapp.models import Restaurant
Restaurant.objects.create(name='Филлер', address='ул. Ленина, 10')
```

```bash
#Добавление тестового продукта
from foodcartapp.models import Product
Product.objects.create(name='Филлер', price=100.00)
```

Чтобы обойти циклическую зависимость в админке Django, достаточно создать один тестовый объект (любой) — это разорвёт замкнутый круг при первоначальном наполнении БД. Удалять такой «заполнитель» (филлер) следует только после того, как в базе появятся как минимум один ресторан и один продукт — тогда связь между сущностями будет корректно установлена и удаление не нарушит целостность данных.

4. Проверьте работоспособность сайта

Чтобы убедиться, что сайт работает, откройте в браузере ваш домен.
Если вместо страницы проекта отображается ошибка (например, 502 Bad Gateway), это значит, что Nginx не может связаться с бэкенд‑сервисом. В таком случае проверьте проброску портов в `docker-compose.yml`, а также слушает ли Gunicorn правильный адрес контейнера (указан в `entrypoint.sh`)

## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org). За основу был взят код проекта [FoodCart](https://github.com/Saibharath79/FoodCart).