from django.urls import path
from django.http import JsonResponse

from . import views, auth_views


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health", health),
    path("auth/register", auth_views.RegisterView.as_view()),
    path("auth/login", auth_views.LoginView.as_view()),
    path("auth/logout", auth_views.LogoutView.as_view()),
    path("auth/me", auth_views.MeView.as_view()),
    path("notes", views.NoteListCreateView.as_view()),
    path("notes/export/", views.NoteExportView.as_view()),
    path("notes/categories", views.NoteCategoriesView.as_view()),
    path("notes/<int:pk>", views.NoteDetailView.as_view()),
    path("notes/<int:pk>/files", views.FileUploadView.as_view()),
    path("files/<int:pk>", views.FileDeleteView.as_view()),
]
