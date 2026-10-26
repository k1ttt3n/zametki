import re

from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, USERNAME_RE


def set_auth_cookies(resp, access, refresh):
    """Access-токен — в httpOnly-куке (JS недоступен), refresh — в отдельной httpOnly-куке."""
    resp.set_cookie(
        settings.ACCESS_TOKEN_COOKIE, access,
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        httponly=True, samesite="Lax", secure=settings.AUTH_COOKIE_SECURE, path="/",
    )
    resp.set_cookie(
        settings.REFRESH_TOKEN_COOKIE, refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True, samesite="Lax", secure=settings.AUTH_COOKIE_SECURE, path="/api/auth",
    )
    return resp


def clear_auth_cookies(resp):
    resp.delete_cookie(settings.ACCESS_TOKEN_COOKIE, path="/")
    resp.delete_cookie(settings.REFRESH_TOKEN_COOKIE, path="/api/auth")
    return resp


def err(field, message):
    return {"errors": {field: message}}


class RegisterView(APIView):
    """POST /api/auth/register — регистрация гостя."""

    permission_classes = []
    authentication_classes = []

    def post(self, request):
        data = request.data or {}
        email = (str(data.get("email", "")) or "").strip().lower()
        username = (str(data.get("username", "")) or "").strip()
        password = str(data.get("password", "") or "")
        confirm = str(data.get("password_confirm", "") or "")

        errors = {}

        if not email:
            errors["email"] = "Введите email"
        elif len(email) > 254 or not re.match(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$", email):
            errors["email"] = "Введите корректный email"
        elif User.objects.filter(email__iexact=email).exists():
            errors["email"] = "Этот email уже занят"

        if not USERNAME_RE.match(username):
            errors["username"] = "Только латиница, цифры и _, от 3 до 30 символов"
        elif User.objects.filter(username__iexact=username).exists():
            errors["username"] = "Этот логин уже занят"

        if not (8 <= len(password) <= 64):
            errors["password"] = "Пароль: от 8 символов, буквы и цифры"
        elif not re.search(r"[A-Za-zА-Яа-я]", password) or not re.search(r"\d", password):
            errors["password"] = "Пароль: от 8 символов, буквы и цифры"

        if password != confirm:
            errors["password_confirm"] = "Пароли не совпадают"

        if errors:
            return Response(err_first(errors), status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(email=email, username=username, password=password)
        return Response(
            {"id": user.id, "email": user.email, "username": user.username, "role": user.role},
            status=status.HTTP_201_CREATED,
        )


def err_first(errors):
    # формат {"errors": {"поле": "сообщение"}} — отдаём первую ошибку, чтобы поле было понятно
    field = next(iter(errors))
    return {"errors": {field: errors[field]}}


class LoginView(APIView):
    """POST /api/auth/login — вход, выдача JWT (access на 24 часа)."""

    permission_classes = []
    authentication_classes = []

    def post(self, request):
        data = request.data or {}
        identifier = (str(data.get("email", "") or data.get("username", "") or "")).strip()
        password = str(data.get("password", "") or "")

        generic = {"errors": {"detail": "Неверный email или пароль"}}

        if not identifier or not password:
            return Response({"errors": {"detail": "Неверный email или пароль"}},
                            status=status.HTTP_400_BAD_REQUEST)

        user = None
        if "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
        else:
            user = User.objects.filter(username__iexact=identifier).first()

        if user is None:
            # проверяем пароль на несуществующем пользователе, чтобы ответ был одинаковым
            authenticate(request, username="nonexistent", password=password)
            return Response(generic, status=status.HTTP_401_UNAUTHORIZED)

        checked = authenticate(request, username=user.email, password=password)
        if checked is None:
            return Response(generic, status=status.HTTP_401_UNAUTHORIZED)

        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(user)
        resp = Response({
            "user": {"id": user.id, "email": user.email,
                     "username": user.username, "role": user.role},
        }, status=status.HTTP_200_OK)
        # токен отдаётся только в httpOnly-куках, в теле ответа его нет
        return set_auth_cookies(resp, str(token.access_token), str(token))


class RefreshView(APIView):
    """POST /api/auth/refresh — обновить access-токен из refresh-куки."""

    permission_classes = []
    authentication_classes = []

    def post(self, request):
        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.tokens import RefreshToken

        raw = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE)
        if not raw:
            return Response({"errors": {"detail": "Нет токена обновления"}},
                            status=status.HTTP_401_UNAUTHORIZED)
        try:
            token = RefreshToken(raw)
            access = str(token.access_token)
        except TokenError:
            return clear_auth_cookies(
                Response({"errors": {"detail": "Сессия истекла, войдите снова"}},
                         status=status.HTTP_401_UNAUTHORIZED))
        resp = Response(status=status.HTTP_204_NO_CONTENT)
        return set_auth_cookies(resp, access, str(token))


class LogoutView(APIView):
    """POST /api/auth/logout — выход; куки с токенами удаляются."""

    def post(self, request):
        resp = Response(status=status.HTTP_204_NO_CONTENT)
        return clear_auth_cookies(resp)


class MeView(APIView):
    """GET /api/auth/me — данные текущего пользователя."""

    def get(self, request):
        u = request.user
        return Response({
            "id": u.id, "email": u.email, "username": u.username, "role": u.role,
        })
