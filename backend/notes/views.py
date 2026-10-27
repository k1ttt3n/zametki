import os
from datetime import date

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Note, File, Category, ALLOWED_FILE_TYPES
from .excel import build_notes_xlsx


def field_error(field, message):
    return {"errors": {field: message}}


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    return s in ("1", "true", "yes", "on")


def filtered_notes(request):
    qs = Note.objects.filter(owner=request.user)
    search = (request.query_params.get("search") or "").strip()
    if search:
        from django.db.models import Q
        qs = qs.filter(Q(title__icontains=search) | Q(text__icontains=search))
    category = (request.query_params.get("category") or "").strip()
    if category:
        qs = qs.filter(category__iexact=category)
    try:
        category_id = int(request.query_params.get("category_id") or 0)
    except ValueError:
        category_id = 0
    if category_id:
        from .category_views import _descendant_ids
        ids = [category_id] + _descendant_ids(Category.objects.get(pk=category_id))
        qs = qs.filter(category_obj_id__in=ids)
    pinned = request.query_params.get("pinned")
    if pinned is not None and str(pinned).strip() != "":
        qs = qs.filter(is_pinned=_parse_bool(pinned))
    favorite = request.query_params.get("favorite")
    if favorite is not None and str(favorite).strip() != "":
        qs = qs.filter(is_favorite=_parse_bool(favorite))
    return qs


class NoteListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        return filtered_notes(request)

    def get(self, request):
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1
        try:
            limit = min(100, max(1, int(request.query_params.get("limit", 12))))
        except ValueError:
            limit = 12

        qs = self.get_queryset(request)
        total = qs.count()
        items = qs[(page - 1) * limit: page * limit]
        return Response({
            "items": [serialize_note(n) for n in items],
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        })

    def post(self, request):
        data = request.data or {}
        errors = validate_note(data)
        if errors:
            return Response({"errors": errors}, status=400)
        category_name, category_obj = _resolve_category(request, data)
        if isinstance(category_name, Response):
            return category_name
        note = Note.objects.create(
            owner=request.user,
            title=str(data.get("title", "")).strip(),
            text=str(data.get("text", "") or ""),
            category=category_name,
            category_obj=category_obj,
            is_pinned=_parse_bool(data.get("is_pinned", False)),
            is_favorite=_parse_bool(data.get("is_favorite", False)),
        )
        return Response(serialize_note(note), status=201)


class NoteDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        note = Note.objects.filter(pk=pk).first()
        if note is None:
            return None, Response(field_error("detail", "Не найдено"), status=404)
        if note.owner_id != request.user.id and request.user.role != "admin":
            # чужая запись не видна
            return None, Response(field_error("detail", "Не найдено"), status=404)
        return note, None

    def get(self, request, pk):
        note, err_resp = self.get_object(request, pk)
        if err_resp:
            return err_resp
        return Response(serialize_note(note))

    def put(self, request, pk):
        note, err_resp = self.get_object(request, pk)
        if err_resp:
            return err_resp
        data = request.data or {}
        errors = validate_note(data)
        if errors:
            return Response({"errors": errors}, status=400)
        category_name, category_obj = _resolve_category(request, data)
        if isinstance(category_name, Response):
            return category_name
        note.title = str(data.get("title", "")).strip()
        note.text = str(data.get("text", "") or "")
        note.category = category_name
        note.category_obj = category_obj
        note.is_pinned = _parse_bool(data.get("is_pinned", False))
        if "is_favorite" in data:
            note.is_favorite = _parse_bool(data.get("is_favorite"))
        note.save()
        return Response(serialize_note(note))

    def delete(self, request, pk):
        note, err_resp = self.get_object(request, pk)
        if err_resp:
            return err_resp
        # файлы удаляются каскадно вместе с записью
        for f in note.files.all():
            try:
                f.file.delete(save=False)
            except Exception:
                pass
        note.delete()
        return Response(status=204)


class NoteCategoriesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cats = (Note.objects.filter(owner=request.user)
                .exclude(category="")
                .values_list("category", flat=True)
                .distinct().order_by("category"))
        return Response({"categories": list(cats)})


class NoteExportView(APIView):
    """GET /api/notes/export/ — выгрузка своих заметок в .xlsx с теми же фильтрами."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.http import HttpResponse
        

        qs = filtered_notes(request)
        filename, content, meta = build_notes_xlsx(qs, prefix="notes")
        resp = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        if meta["truncated"]:
            resp["X-Export-Warning"] = "more than 10000 rows"
        return resp


class FileUploadView(APIView):
    """POST /api/notes/:id/files — загрузка файла к своей заметке."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        note = Note.objects.filter(pk=pk).first()
        if note is None:
            return Response(field_error("detail", "Не найдено"), status=404)
        if note.owner_id != request.user.id:
            return Response(field_error("detail", "Нет доступа"), status=403)

        upload = request.FILES.get("file")
        if upload is None:
            return Response(field_error("file", "Прикрепите файл"), status=400)

        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        if upload.size > max_bytes:
            return Response(
                field_error("file", f"Файл больше {settings.MAX_UPLOAD_MB} МБ"),
                status=413,
            )

        mime = (upload.content_type or "").lower()
        ext = os.path.splitext(upload.name)[1].lower()
        allowed_exts = set(ALLOWED_FILE_TYPES.values())
        if mime not in ALLOWED_FILE_TYPES and ext not in allowed_exts:
            return Response(
                field_error("file", "Допустимы изображения, PDF и TXT"),
                status=415,
            )

        f = File.objects.create(
            note=note,
            file=upload,
            original_name=upload.name[:255],
            mime=mime or "application/octet-stream",
            size_bytes=upload.size,
        )
        return Response(serialize_file(f), status=201)


class FileDeleteView(APIView):
    """DELETE /api/files/:id — удаление файла вместе с физическим файлом."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        f = File.objects.filter(pk=pk).select_related("note").first()
        if f is None:
            return Response(field_error("detail", "Не найдено"), status=404)
        if f.note.owner_id != request.user.id:
            return Response(field_error("detail", "Нет доступа"), status=403)
        f.delete()
        return Response(status=204)



def _resolve_category(request, data):
    """Возвращает (имя, объект) либо (ErrorResponse, None).

    category_id — выбор готовой категории из дерева;
    new_category — создание новой ветки (опционально внутри parent_id);
    category (текст) — обратная совместимость со старыми клиентами.
    """
    from .category_views import _clean_name
    cid = data.get("category_id")
    if cid not in (None, "", 0, "0", "null"):
        try:
            cat = Category.objects.get(pk=int(cid), owner=request.user)
        except (Category.DoesNotExist, ValueError, TypeError):
            return Response(field_error("category", "Категория не найдена"), status=400), None
        return cat.name, cat

    if data.get("new_category"):
        name, err = _clean_name(data.get("new_category"))
        if err:
            return Response(field_error("category", err), status=400), None
        pid = data.get("new_category_parent")
        parent = None
        if pid not in (None, "", 0, "0", "null"):
            parent = Category.objects.filter(pk=int(pid) if str(pid).isdigit() else 0,
                                             owner=request.user).first()
            if parent is None:
                return Response(field_error("category", "Родительская категория не найдена"), status=400), None
        cat, created = Category.objects.get_or_create(owner=request.user, parent=parent, name=name)
        return cat.name, cat

    raw = str(data.get("category", "") or "").strip()
    if raw:
        cat = Category.objects.filter(owner=request.user, name__iexact=raw,
                                      parent__isnull=True).first()
        return raw, cat
    return "", None


def validate_note(data):
    errors = {}
    title = str(data.get("title", "") or "").strip()
    if not title:
        errors["title"] = "Введите название (до 120 символов)"
    elif len(title) > 120:
        errors["title"] = "Название не длиннее 120 символов"

    text = str(data.get("text", "") or "")
    if len(text) > 10000:
        errors["text"] = "Текст заметки не длиннее 10000 символов"

    category = str(data.get("category", "") or "")
    if len(category) > 64:
        errors["category"] = "Категория не длиннее 64 символов"
    return errors


def serialize_note(note):
    return {
        "id": note.id,
        "title": note.title,
        "text": note.text,
        "category": note.category,
        "category_id": note.category_obj_id,
        "is_pinned": note.is_pinned,
        "is_favorite": note.is_favorite,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
        "files": [serialize_file(f) for f in note.files.all()],
    }


def serialize_file(f):
    url = None
    if f.file:
        try:
            url = f.file.url
        except Exception:
            url = None
    return {
        "id": f.id,
        "original_name": f.original_name,
        "mime": f.mime,
        "size_bytes": f.size_bytes,
        "url": url,
        "created_at": f.created_at.isoformat(),
    }
