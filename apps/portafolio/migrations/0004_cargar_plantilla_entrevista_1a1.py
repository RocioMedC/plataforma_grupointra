from django.db import migrations


def cargar_plantilla(apps, schema_editor):
    from apps.portafolio.services_entrevista import cargar_plantilla_entrevista_1a1
    cargar_plantilla_entrevista_1a1()


class Migration(migrations.Migration):
    dependencies = [('portafolio', '0003_instrumento_version_and_more')]
    operations = [migrations.RunPython(cargar_plantilla, migrations.RunPython.noop)]
