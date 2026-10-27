from django.contrib import admin
from .models import User, Note, File, Category


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "created_at")


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "category", "is_pinned", "updated_at")
    list_filter = ("category", "is_pinned")


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "note", "mime", "size_bytes")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "parent")
