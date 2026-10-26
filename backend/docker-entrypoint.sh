#!/bin/sh
set -e

echo "==> Ждём готовности PostgreSQL (${DB_HOST:-db}:${DB_PORT:-5432})..."
i=0
until python -c "
import socket, sys
s = socket.socket(); s.settimeout(2)
try:
    s.connect(('${DB_HOST:-db}', int('${DB_PORT:-5432}')))
except Exception:
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; do
  i=$((i+1))
  if [ "$i" -gt 60 ]; then echo "!! БД недоступна, выхожу"; exit 1; fi
  sleep 1
done
echo "==> БД доступна."

echo "==> Применяем миграции..."
python manage.py migrate --noinput

echo "==> Собираем статику..."
python manage.py collectstatic --noinput || true

if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "==> Создаём суперпользователя (если ещё нет)..."
  python - <<'PY' || true
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "notesapp.settings")
django.setup()
from notes.models import User
if not User.objects.filter(email__iexact=os.environ["DJANGO_SUPERUSER_EMAIL"]).exists():
    User.objects.create_superuser(
        email=os.environ["DJANGO_SUPERUSER_EMAIL"],
        username=os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin"),
        password=os.environ["DJANGO_SUPERUSER_PASSWORD"],
    )
    print("superuser created")
else:
    print("superuser already exists")
PY
fi

echo "==> Запускаем gunicorn..."
exec gunicorn notesapp.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout 60
