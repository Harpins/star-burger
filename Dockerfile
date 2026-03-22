# Dockerfile для Django + Gunicorn

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    SECRET_KEY=$SECRET_KEY \
    YA_API_KEY=$YA_API_KEY \
    ALLOWED_HOSTS=$ALLOWED_HOSTS \
    DEBUG=$DEBUG \
    ROLLBAR_TOKEN=$ROLLBAR_TOKEN \
    ROLLBAR_ENABLED=$ROLLBAR_ENABLED \
    DATABASE_URL=$DATABASE_URL \
    CSRF_TRUSTED_ORIGINS=$CSRF_TRUSTED_ORIGINS

WORKDIR /star-burger

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        openssl \
        curl \
        wget \
        build-essential \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir \
    --index-url http://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple \
    --trusted-host mirrors.tuna.tsinghua.edu.cn \
    --timeout=180 \
    -r requirements.txt

COPY package*.json ./
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash - \
    && apt-get install -y nodejs \
    && npm ci --omit=dev \
    && npm cache clean --force \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN npm run build

RUN python manage.py collectstatic --noinput --clear

EXPOSE 8000

#Gunicorn

CMD ["gunicorn", "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "star_burger.wsgi:application"]