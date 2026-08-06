from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("certificacion_intera", "0003_certificacion_intera"),
    ]

    operations = [
        migrations.AddField(
            model_name="procesocertificacion",
            name="ciclo_escolar",
            field=models.CharField(
                blank=True,
                max_length=30,
            ),
        ),
    ]