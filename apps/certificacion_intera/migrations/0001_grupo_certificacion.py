from django.db import migrations


def crear_grupo_certificacion(apps, schema_editor):
    Group = apps.get_model(
        "auth",
        "Group",
    )
    Group.objects.get_or_create(
        name="Certificación",
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            "auth",
            "0012_alter_user_first_name_max_length",
        ),
    ]

    operations = [
        migrations.RunPython(
            crear_grupo_certificacion,
        ),
    ]