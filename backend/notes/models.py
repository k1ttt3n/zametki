import re
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra):
        if not email:
            raise ValueError("Email обязателен")
        # нормализуем перед сохранением — уникальный индекс в Postgres
        # учитывает регистр (user@Mail.ru и user@mail.ru были бы разными)
        user = self.model(email=self.normalize_email(email).lower(),
                          username=username.strip(), **extra)
        user.set_password(password)  # пароль хранится хешем (PBKDF2)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra):
        extra.setdefault("role", "admin")
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, username, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [("user", "Пользователь"), ("admin", "Администратор")]

    email = models.EmailField("email", unique=True, max_length=254)
    username = models.CharField("логин", unique=True, max_length=30)
    role = models.CharField("роль", max_length=10, choices=ROLE_CHOICES, default="user")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        constraints = [
            # Регистронезависимая уникальность email на уровне БД
            # (Postgres и sqlite >= 3.40; Django сам пропускает там, где
            # выражения в индексах не поддерживаются).
            models.UniqueConstraint(Lower("email"), name="uniq_user_email_lower"),
        ]

    objects = UserManager()

    def __str__(self):
        return self.username


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")


class Category(models.Model):
    """Дерево категорий: parent=None — корневая ветка."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField("название", max_length=64)
    parent = models.ForeignKey("self", null=True, blank=True,
                               on_delete=models.CASCADE, related_name="children")

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "parent", "name"],
                                    name="uniq_category_per_parent"),
        ]

    def clean(self):
        super().clean()
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValueError("Название категории не может быть пустым")
        if len(self.name) > 64:
            raise ValueError("Название категории не длиннее 64 символов")
        # запрет циклов: родитель не может быть нашим потомком
        seen, node = {self.pk}, self.parent
        while node is not None:
            if node.pk in seen:
                raise ValueError("Нельзя переместить категорию внутрь самой себя")
            seen.add(node.pk)
            node = node.parent

    def __str__(self):
        return self.name


class Note(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes")
    title = models.CharField("заголовок", max_length=120)
    text = models.TextField("текст", max_length=10000, blank=True)
    category = models.CharField("категория", max_length=64, blank=True)
    category_obj = models.ForeignKey(Category, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="notes")
    is_pinned = models.BooleanField("закреплена", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-updated_at"]

    def clean(self):
        super().clean()
        self.title = (self.title or "").strip()
        if not self.title:
            raise ValueError("Введите название (до 120 символов)")
        if len(self.title) > 120:
            raise ValueError("Название не длиннее 120 символов")
        if len(self.text or "") > 10000:
            raise ValueError("Текст заметки не длиннее 10000 символов")
        if len(self.category or "") > 64:
            raise ValueError("Категория не длиннее 64 символов")

    def __str__(self):
        return self.title


ALLOWED_FILE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
}


def stored_file_name(instance, filename):
    ext = ""
    m = re.search(r"\.[A-Za-z0-9]{1,8}$", filename or "")
    if m:
        ext = m.group(0).lower()
    return f"notes/{instance.note_id}/{uuid.uuid4().hex}{ext}"


class File(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to=stored_file_name, max_length=255)
    original_name = models.CharField(max_length=255)
    stored_name = models.CharField(max_length=255, blank=True)
    mime = models.CharField(max_length=100)
    size_bytes = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        new = self.pk is None
        super().save(*args, **kwargs)
        if new and self.file and not self.stored_name:
            self.stored_name = self.file.name.split("/")[-1]
            super().save(update_fields=["stored_name"])

    def delete(self, *args, **kwargs):
        if self.file:
            try:
                self.file.delete(save=False)
            except Exception:
                pass
        super().delete(*args, **kwargs)
