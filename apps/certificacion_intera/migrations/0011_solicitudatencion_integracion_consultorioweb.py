import uuid

from django.db import migrations, models


def asignar_identidades(apps, schema_editor):
    SolicitudAtencion = apps.get_model(
        'certificacion_intera',
        'SolicitudAtencion',
    )

    for solicitud in SolicitudAtencion.objects.filter(
        external_request_id__isnull=True,
    ):
        solicitud.external_request_id = uuid.uuid4()
        solicitud.idempotency_key = uuid.uuid4()
        solicitud.save(
            update_fields=[
                'external_request_id',
                'idempotency_key',
            ],
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            'certificacion_intera',
            '0010_solicitudatencion',
        ),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudatencion',
            name='external_request_id',
            field=models.UUIDField(
                null=True,
                editable=False,
            ),
        ),
        migrations.AddField(
            model_name='solicitudatencion',
            name='idempotency_key',
            field=models.UUIDField(
                null=True,
                editable=False,
            ),
        ),
        migrations.AddField(
            model_name='solicitudatencion',
            name='integration_status',
            field=models.CharField(
                max_length=22,
                default='pendiente_envio',
                choices=[
                    (
                        'pendiente_envio',
                        'Pendiente de envío',
                    ),
                    (
                        'enviando',
                        'Enviando',
                    ),
                    (
                        'enviada',
                        'Enviada',
                    ),
                    (
                        'error_comunicacion',
                        'Error de comunicación',
                    ),
                ],
            ),
        ),
        migrations.AddField(
            model_name='solicitudatencion',
            name='remote_status',
            field=models.CharField(
                max_length=30,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name='solicitudatencion',
            name='sent_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name='solicitudatencion',
            name='last_status_check_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name='solicitudatencion',
            name='last_response_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name='solicitudatencion',
            name='last_error_code',
            field=models.CharField(
                max_length=30,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name='solicitudatencion',
            name='last_error_message',
            field=models.CharField(
                max_length=250,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name='solicitudatencion',
            name='send_attempts',
            field=models.PositiveIntegerField(
                default=0,
            ),
        ),
        migrations.AddField(
            model_name='solicitudatencion',
            name='remote_internal_request_id',
            field=models.CharField(
                max_length=100,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name='solicitudatencion',
            name='remote_updated_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
            ),
        ),
        migrations.RunPython(
            asignar_identidades,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='solicitudatencion',
            name='external_request_id',
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
            ),
        ),
        migrations.AlterField(
            model_name='solicitudatencion',
            name='idempotency_key',
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
            ),
        ),
    ]