import re

from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, USERNAME_RE


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
        return Response({
            "token": str(token.access_token),
            "refresh": str(token),
            "user": {"id": user.id, "email": user.email,
                     "username": user.username, "role": user.role},
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/auth/logout — выход; токен удаляется на клиенте."""

    def post(self, request):
        resp = Response(status=status.HTTP_204_NO_CONTENT)
        resp.delete_cookie("sessionid")
        return resp


class MeView(APIView):
    """GET /api/auth/me — данные текущего пользователя."""

    def get(self, request):
        u = request.user
        return Response({
            "id": u.id, "email": u.email, "username": u.username, "role": u.role,
        })
