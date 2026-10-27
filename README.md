# Заметки — Django REST + React

Веб-приложение «Заметки»: регистрация, вход (JWT), CRUD заметок с категориями,
поиск/фильтрация/пагинация, закрепление, загрузка файлов (изображения/PDF/TXT до 10 МБ),
экспорт в .xlsx, админка Django.

## Структура

```
backend/    # Django + DRF + SimpleJWT + WhiteNoise + gunicorn
frontend/   # React 18 + Vite + react-router + axios (сборка отдаётся nginx)
docker-compose.yml
.env.example
```

## Запуск через Docker (продакшн-режим)

Осталось только выполнить сборку и старт:

```bash
cp .env.example .env      # заполнить секреты (SECRET_KEY, пароли БД, данные админа)
docker compose up -d --build
```

Приложение будет доступно на http://localhost:8080
(port меняется переменной `WEB_PORT` в `.env`).

Первый старт автоматически:
- применяет миграции;
- собирает статику;
- создаёт суперпользователя из `DJANGO_SUPERUSER_*` (админка: /admin).

Полезные команды:

```bash
docker compose logs -f backend     # логи API
docker compose exec backend python manage.py createsuperuser
docker compose down                # остановить
docker compose down -v             # удалить вместе с данными БД и файлов
```

## Локальная разработка (без Docker)

Backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000    # sqlite, если DB_HOST не задан
```

Frontend:

```bash
cd frontend
npm ci
npm run dev                        # http://localhost:3000, прокси /api → :8000
```

Для дев-прокси в `frontend/vite.config.js` добавьте:

```js
server: { port: 3000, proxy: { '/api': 'http://localhost:8000', '/media': 'http://localhost:8000' } }
```

(в production nginx сам проксирует `/api`, `/media`, `/static`, `/admin` на backend).

## Переменные окружения (backend)

| Переменная | Описание | По умолчанию |
|---|---|---|
| DJANGO_SECRET_KEY | секрет Django | dev-заглушка |
| DJANGO_DEBUG | режим отладки | 1 |
| DJANGO_ALLOWED_HOSTS | хосты через запятую | * |
| CORS_ALLOWED_ORIGINS | разрешённые origin через запятую | пусто |
| DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD | PostgreSQL (если DB_HOST задан) | sqlite |
| MAX_UPLOAD_MB | лимит размера файла | 10 |
| LOGIN_RATE_LIMIT | попыток входа с IP в минуту | 10 |
| GUNICORN_WORKERS | воркеров gunicorn | 3 |
