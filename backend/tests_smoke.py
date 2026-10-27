"""Интеграционный тест: rate limit 10/мин + JWT в httpOnly-куках.

Запуск (sqlite, без PostgreSQL):
    python tests_smoke.py
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "notesapp.settings")
os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ.setdefault("AUTH_COOKIE_SECURE", "0")
# Тестовая изолированная sqlite-БД: задаём через переменную окружения ДО
# django.setup(), чтобы настройки не успели открыть коннект к dev-файлу
# db.sqlite3 (в нём остаются тестовые пользователи и мешают миграции).
test_db = os.path.join(os.getcwd(), "test_db.sqlite3")
if os.path.exists(test_db):
    os.remove(test_db)
os.environ["DB_SQLITE_PATH"] = test_db
django.setup()

from django.conf import settings  # noqa: E402

assert settings.DATABASES["default"]["NAME"] == test_db, \
    "тест должен работать на изолированной БД, а не на db.sqlite3"

from django.core.management import call_command  # noqa: E402

call_command("migrate", verbosity=0)

from notes import throttle  # noqa: E402
from notes.models import User  # noqa: E402

User.objects.create_user(email="A@A.com", username="user_a", password="passw1234")

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

    # --- дерево категорий + выбор/создание категории при добавлении заметки
    c = fresh()
    c.post("/api/auth/login", data='{"email":"a@a.com","password":"passw1234"}',
           content_type="application/json")
    c.get("/api/csrf")
    csrf = c.cookies["csrftoken"].value

    r = c.post("/api/categories", data='{"name":"Работа"}',
               content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    assert r.status_code == 201, r.content
    work_id = r.json()["id"]

    r = c.post("/api/categories", data='{"name":"Проекты","parent":%d}' % work_id,
               content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    assert r.status_code == 201, r.content
    proj_id = r.json()["id"]

    # дубль имени в одном родителе -> 409
    r = c.post("/api/categories", data='{"name":"Работа"}',
               content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    assert r.status_code == 409, r.status_code

    # цикл запрещён: Работа внутрь Проектов
    r = c.patch("/api/categories/%d" % work_id, data='{"parent":%d}' % proj_id,
                content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    assert r.status_code == 400, r.status_code

    # дерево
    r = c.get("/api/categories/tree")
    tree = r.json()["tree"]
    assert tree[0]["name"] == "Работа" and tree[0]["children"][0]["name"] == "Проекты", tree

    # заметка с готовой категорией по category_id
    r = c.post("/api/notes", data='{"title":"N1","category_id":%d}' % proj_id,
               content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    assert r.status_code == 201 and r.json()["category_id"] == proj_id, r.content

    # заметка с созданием новой категории прямо из формы
    r = c.post("/api/notes", data='{"title":"N2","new_category":"Личное","new_category_parent":null}',
               content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    assert r.status_code == 201, r.content
    personal_id = r.json()["category_id"]
    assert personal_id, r.content

    # фильтр по ветке дерева включает дочерние категории
    r = c.get("/api/notes", {"category_id": work_id})
    titles = [i["title"] for i in r.json()["items"]]
    assert titles == ["N1"], titles

    # удаление родителя снимает category_obj у заметок (SET_NULL)
    r = c.delete("/api/categories/%d" % proj_id, HTTP_X_CSRFTOKEN=csrf)
    assert r.status_code == 204
    r = c.get("/api/notes", {"category_id": work_id})
    assert r.json()["total"] == 0

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

    # --- регистрация: понятные ошибки вместо «Ошибка регистрации» -------------
    # email уже занят (в другом регистре) -> 400 с конкретным сообщением
    c = fresh()
    r = c.post("/api/auth/register", data=(
        '{"email":"A@A.com","username":"other_user","password":"passw1234",'
        '"password_confirm":"passw1234"}'), content_type="application/json")
    assert r.status_code == 400 and "email" in r.json()["errors"], r.content

    # полностью цифровой пароль -> 400 (проверяется на этапе валидации, до БД)
    c = fresh()
    r = c.post("/api/auth/register", data=(
        '{"email":"d@d.com","username":"digits_only","password":"12345678",'
        '"password_confirm":"12345678"}'), content_type="application/json")
    assert r.status_code == 400 and "password" in r.json()["errors"], r.content

    # IntegrityError (гонка двух параллельных регистраций) должен дать 409 с
    # конкретным текстом, а не абстрактную ошибку. Эмулируем гонку: в момент
    # pre-check пользователя нет, но к моменту INSERT он уже есть.
    from notes import auth_views
    orig_create_user = auth_views.User.objects.create_user

    def racing_create_user(*a, **kw):
        auth_views.User.objects.create_user = orig_create_user  # восстановить
        # «параллельный» запрос создал точно такой же email/логин до нашего INSERT
        orig_create_user(email="ghost@g.com", username="ghost_v", password="passw1234")
        return orig_create_user(*a, **kw)  # обычный путь -> IntegrityError

    auth_views.User.objects.create_user = racing_create_user
    c = fresh()
    r = c.post("/api/auth/register", data=(
        '{"email":"ghost@g.com","username":"ghost_v","password":"passw1234",'
        '"password_confirm":"passw1234"}'), content_type="application/json")
    assert r.status_code == 409, (r.status_code, r.content)
    assert "занят" in r.json()["errors"]["detail"], r.content

    # после 409 соединение живо — следующая регистрация проходит (нет каскада 500)
    c = fresh()
    r = c.post("/api/auth/register", data=(
        '{"email":"ok@ok.com","username":"user_ok","password":"passw1234",'
        '"password_confirm":"passw1234"}'), content_type="application/json")
    assert r.status_code == 201, (r.status_code, r.content)

    print("ALL OK")


if __name__ == "__main__":
    main()
