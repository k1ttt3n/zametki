from django.urls import path
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from . import views, auth_views, category_views


def health(request):
    return JsonResponse({"status": "ok"})


@require_GET
@ensure_csrf_cookie
def csrf_token(request):
    """GET /api/csrf — выдаёт куку csrftoken для запросов с JWT-куками."""
    return JsonResponse({"ok": True})


urlpatterns = [
    path("health", health),
    path("csrf", csrf_token),
    path("auth/register", auth_views.RegisterView.as_view()),
    path("auth/login", auth_views.LoginView.as_view()),
    path("auth/refresh", auth_views.RefreshView.as_view()),
    path("auth/logout", auth_views.LogoutView.as_view()),
    path("auth/me", auth_views.MeView.as_view()),
    path("categories/tree", category_views.CategoryTreeView.as_view()),
    path("categories", category_views.CategoryListCreateView.as_view()),
    path("categories/<int:pk>", category_views.CategoryDetailView.as_view()),
    path("notes", views.NoteListCreateView.as_view()),
    path("notes/export/", views.NoteExportView.as_view()),
    path("notes/categories", views.NoteCategoriesView.as_view()),
    path("notes/<int:pk>", views.NoteDetailView.as_view()),
    path("notes/<int:pk>/files", views.FileUploadView.as_view()),
    path("files/<int:pk>", views.FileDeleteView.as_view()),
]
