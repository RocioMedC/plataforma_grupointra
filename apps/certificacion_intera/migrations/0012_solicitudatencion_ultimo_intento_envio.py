from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "certificacion_intera",
            "0011_solicitudatencion_integracion_consultorioweb",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudatencion",
            name="last_send_attempt_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),
    ]