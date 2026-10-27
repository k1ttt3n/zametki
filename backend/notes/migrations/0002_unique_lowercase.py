from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0001_initial"),
    ]

    operations = [
        # Нормализация: email хранится в нижнем регистре — защищает от
        # дублей вида User@mail.ru / user@mail.ru на уровне БД (Postgres).
        migrations.RunPython(
            lambda apps, schema_editor: (
                apps.get_model("notes", "User").objects.update(email=Lower("email"))
            ),
            lambda apps, schema_editor: None,
        ),
        # AddConstraint перенесён в 0003: на sqlite выражения в
        # UniqueConstraint не поддерживаются и Django пропускает их молча,
        # из-за чего state/БД расходились с моделями.
    ]
