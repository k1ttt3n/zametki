import re

from django.db import IntegrityError
from django.db.models import Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Note


def _err(field, message, code=400):
    return Response({"errors": {field: message}}, status=code)


def _clean_name(raw):
    name = str(raw or "").strip()
    name = re.sub(r"\s+", " ", name)
    if not name:
        return None, "Название категории не может быть пустым"
    if len(name) > 64:
        return None, "Название категории не длиннее 64 символов"
    return name, None


def _get_own(request, pk):
    cat = Category.objects.filter(pk=pk).first()
    if cat is None or cat.owner_id != request.user.id:
        return None, _err("detail", "Не найдено", 404)
    return cat, None


def _descendant_ids(root):
    """BFS по детям — id всех узлов под root (root не входит)."""
    ids, frontier = [], [root.pk]
    while frontier:
        children = list(Category.objects.filter(parent_id__in=frontier)
                        .values_list("id", flat=True))
        ids.extend(children)
        frontier = children
    return ids


class CategoryTreeView(APIView):
    """GET /api/categories/tree — дерево категорий пользователя."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cats = list(Category.objects.filter(owner=request.user)
                    .order_by("name").values("id", "name", "parent_id"))
        note_counts = {}
        for row in (Note.objects.filter(owner=request.user, category_obj__isnull=False)
                    .values("category_obj").annotate(c=Count("id"))):
            note_counts[row["category_obj"]] = row["c"]
        by_parent = {}
        for c in cats:
            by_parent.setdefault(c["parent_id"], []).append(c)

        def build(parent_id):
            out = []
            for c in by_parent.get(parent_id, []):
                out.append({
                    "id": c["id"],
                    "name": c["name"],
                    "parent": c["parent_id"],
                    "note_count": note_counts.get(c["id"], 0),
                    "children": build(c["id"]),
                })
            return out

        return Response({"tree": build(None)})


class CategoryListCreateView(APIView):
    """POST /api/categories — создать категорию (можно с parent)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data or {}
        name, err = _clean_name(data.get("name"))
        if err:
            return _err("name", err)
        parent = None
        pid = data.get("parent")
        if pid not in (None, "", "null"):
            try:
                parent = Category.objects.get(pk=int(pid), owner=request.user)
            except (Category.DoesNotExist, ValueError, TypeError):
                return _err("parent", "Родительская категория не найдена", 404)
        if Category.objects.filter(owner=request.user, parent=parent, name=name).exists():
            where = f"«{parent.name}»" if parent else "в корне"
            return _err("name", f"Категория «{name}» уже существует {where}", 409)
        try:
            cat = Category.objects.create(owner=request.user, name=name, parent=parent)
        except IntegrityError:
            where = f"«{parent.name}»" if parent else "в корне"
            return _err("name", f"Категория «{name}» уже существует {where}", 409)
        return Response({
            "id": cat.id, "name": cat.name,
            "parent": cat.parent_id, "note_count": 0, "children": [],
        }, status=201)


class CategoryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        cat, err_resp = _get_own(request, pk)
        if err_resp:
            return err_resp
        data = request.data or {}
        errors = {}
        if "name" in data:
            name, err = _clean_name(data.get("name"))
            if err:
                errors["name"] = err
            else:
                cat.name = name
        if "parent" in data:
            pid = data.get("parent")
            if pid in (None, "", "null"):
                cat.parent = None
            else:
                try:
                    parent = Category.objects.get(pk=int(pid), owner=request.user)
                except (Category.DoesNotExist, ValueError, TypeError):
                    errors["parent"] = "Родительская категория не найдена"
                else:
                    if parent.pk == cat.pk or parent.pk in _descendant_ids(cat):
                        errors["parent"] = "Нельзя переместить категорию внутрь самой себя"
                    else:
                        cat.parent = parent
        if errors:
            return Response({"errors": errors}, status=400)
        try:
            cat.full_clean(exclude=["owner", "created_at"] if hasattr(cat, "created_at") else None)
        except Exception as e:
            msg = getattr(e, "message_dict", None) or {"name": [str(e)]}
            return _err(next(iter(msg)), msg[next(iter(msg))][0])
        try:
            cat.save()
        except IntegrityError:
            return _err("name", "Категория с таким названием уже существует в этом разделе", 409)
        return Response({"id": cat.id, "name": cat.name, "parent": cat.parent_id})

    def delete(self, request, pk):
        cat, err_resp = _get_own(request, pk)
        if err_resp:
            return err_resp
        cat.delete()  # дети удаляются каскадно, у заметок category_obj -> NULL
        return Response(status=204)
