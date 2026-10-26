"""Интеграционный тест: rate limit 10/мин + JWT в httpOnly-куках.

Запуск (sqlite, без PostgreSQL):
    python tests_smoke.py
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "notesapp.settings")
os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ.setdefault("AUTH_COOKIE_SECURE", "0")
django.setup()

from django.conf import settings  # noqa: E402

settings.DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:",
    "ATOMIC_REQUESTS": False, "AUTOCOMMIT": True, "TIME_ZONE": None,
    "OPTIONS": {}, "USER": "", "PASSWORD": "", "HOST": "", "PORT": "",
    "CONN_MAX_AGE": 0, "TEST": {},
}

from django.core.management import call_command  # noqa: E402

call_command("migrate", "--run-syncdb", verbosity=0)

from notes import throttle  # noqa: E402
from notes.models import User  # noqa: E402

User.objects.create_user(email="a@a.com", username="user_a", password="passw1234")

from django.test import Client  # noqa: E402


def fresh():
    throttle._attempts.clear()
    return Client()


def main():
    c = fresh()
    # регистрация через API
    r = c.post("/api/auth/register", data=(
        '{"email":"n@n.com","username":"user_n","password":"passw1234",'
        '"password_confirm":"passw1234"}'), content_type="application/json")
    assert r.status_code == 201, (r.status_code, r.content)

    # вход: токен только в куках, не в теле
    c = fresh()
    r = c.post("/api/auth/login", data='{"email":"a@a.com","password":"passw1234"}',
               content_type="application/json")
    assert r.status_code == 200 and b'"token"' not in r.content
    assert c.cookies["access_token"].value and c.cookies["access_token"]["httponly"]
    assert c.cookies["refresh_token"].value

    # доступ по куке без заголовка Authorization
    assert c.get("/api/auth/me").status_code == 200

    # запись — через CSRF-токен
    c.get("/api/csrf")
    csrf = c.cookies["csrftoken"].value
    r = c.post("/api/notes", data='{"title":"T1","text":"hello"}',
               content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    assert r.status_code == 201, r.content

    # refresh и logout чистят куки
    assert c.post("/api/auth/refresh", HTTP_X_CSRFTOKEN=csrf).status_code == 204
    assert c.post("/api/auth/logout", HTTP_X_CSRFTOKEN=csrf).status_code == 204
    assert c.cookies["access_token"].value == ""
    assert c.get("/api/auth/me").status_code == 401

    # rate limit: ровно 10 попыток в минуту, 11-я — 429 (login+register вместе)
    c = fresh()
    for i in range(10):
        rr = c.post("/api/auth/login", data='{"email":"a@a.com","password":"wrong11111"}',
                    content_type="application/json")
        assert rr.status_code == 401, (i, rr.status_code)
    rr = c.post("/api/auth/register", data=(
        '{"email":"z@z.com","username":"user_z","password":"passw1234",'
        '"password_confirm":"passw1234"}'), content_type="application/json")
    assert rr.status_code == 429, rr.status_code

    print("ALL OK")


if __name__ == "__main__":
    main()
