from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import functions


def migrate_text_categories(apps, schema_editor):
    Note = apps.get_model("notes", "Note")
    Category = apps.get_model("notes", "Category")
    for note in Note.objects.exclude(category="").filter(category_obj__isnull=True):
        cat, _ = Category.objects.get_or_create(
            owner_id=note.owner_id, parent=None, name=note.category.strip()[:64],
        )
        if cat:
            note.category_obj_id = cat.pk
            note.save(update_fields=["category_obj"])


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0002_unique_lowercase"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                models.functions.Lower("email"), name="uniq_user_email_lower",
            ),
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, verbose_name="название")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="categories", to=settings.AUTH_USER_MODEL)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="notes.category")),
            ],
            options={
                "verbose_name_plural": "categories",
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="category",
            constraint=models.UniqueConstraint(fields=("owner", "parent", "name"), name="uniq_category_per_parent"),
        ),
        migrations.AddField(
            model_name="note",
            name="category_obj",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notes", to="notes.category"),
        ),
        # перенос существующих текстовых категорий в дерево (корневые узлы)
        migrations.RunPython(migrate_text_categories, reverse_code=migrations.RunPython.noop),
    ]


