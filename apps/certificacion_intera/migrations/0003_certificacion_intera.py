import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("certificacion_intera", "0002_escuela"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Instrumento",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nombre", models.CharField(max_length=150)),
                ("clave", models.SlugField(max_length=50, unique=True)),
                ("descripcion", models.TextField(blank=True)),
                ("instrucciones", models.TextField(blank=True)),
                ("activo", models.BooleanField(default=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Instrumento",
                "verbose_name_plural": "Instrumentos",
                "ordering": ["nombre"],
            },
        ),
        migrations.CreateModel(
            name="ProcesoCertificacion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "nombre",
                    models.CharField(
                        default="Proceso de certificación",
                        max_length=150,
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("configuracion", "Configuración"),
                            ("aplicacion", "Aplicación de instrumentos"),
                            ("seguimiento", "Seguimiento"),
                            ("consejeria", "Consejerías"),
                            ("cerrado", "Cerrado"),
                        ],
                        default="configuracion",
                        max_length=20,
                    ),
                ),
                ("fecha_inicio", models.DateField()),
                (
                    "fecha_cierre",
                    models.DateField(
                        blank=True,
                        null=True,
                    ),
                ),
                ("observaciones", models.TextField(blank=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                (
                    "creado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "escuela",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="procesos",
                        to="certificacion_intera.escuela",
                    ),
                ),
            ],
            options={
                "verbose_name": "Proceso de certificación",
                "verbose_name_plural": "Procesos de certificación",
                "ordering": ["-fecha_inicio", "-id"],
            },
        ),
        migrations.CreateModel(
            name="PreguntaInstrumento",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("orden", models.PositiveIntegerField(default=0)),
                ("texto", models.TextField()),
                (
                    "clave",
                    models.CharField(
                        blank=True,
                        max_length=50,
                    ),
                ),
                (
                    "tipo_respuesta",
                    models.CharField(
                        choices=[
                            ("opcion_unica", "Opción única"),
                            ("opcion_multiple", "Opción múltiple"),
                            ("escala", "Escala numérica / Likert"),
                            ("si_no", "Sí / No"),
                            ("texto_libre", "Texto libre"),
                        ],
                        default="opcion_unica",
                        max_length=20,
                    ),
                ),
                (
                    "opciones",
                    models.JSONField(
                        blank=True,
                        help_text="Lista de objetos {valor, etiqueta}.",
                        null=True,
                    ),
                ),
                ("requerida", models.BooleanField(default=True)),
                (
                    "instrumento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="preguntas",
                        to="certificacion_intera.instrumento",
                    ),
                ),
            ],
            options={
                "verbose_name": "Pregunta de instrumento",
                "verbose_name_plural": "Preguntas de instrumentos",
                "ordering": ["instrumento", "orden", "id"],
            },
        ),
        migrations.CreateModel(
            name="Participante",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nombre", models.CharField(max_length=200)),
                ("numero_alumno", models.CharField(max_length=50)),
                (
                    "correo",
                    models.EmailField(
                        blank=True,
                        max_length=254,
                    ),
                ),
                (
                    "telefono",
                    models.CharField(
                        blank=True,
                        max_length=30,
                    ),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "proceso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participantes",
                        to="certificacion_intera.procesocertificacion",
                    ),
                ),
            ],
            options={
                "verbose_name": "Participante",
                "verbose_name_plural": "Participantes",
                "ordering": ["nombre"],
                "unique_together": {("proceso", "numero_alumno")},
            },
        ),
        migrations.CreateModel(
            name="ConfiguracionInstrumento",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("requerido", models.BooleanField(default=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "instrumento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="configuraciones",
                        to="certificacion_intera.instrumento",
                    ),
                ),
                (
                    "proceso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="configuraciones_instrumento",
                        to="certificacion_intera.procesocertificacion",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configuración de instrumento",
                "verbose_name_plural": "Configuraciones de instrumentos",
                "unique_together": {("proceso", "instrumento")},
            },
        ),
        migrations.CreateModel(
            name="Canalizacion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("fecha", models.DateField()),
                ("motivo", models.CharField(max_length=250)),
                ("observaciones", models.TextField(blank=True)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendiente", "Pendiente"),
                            ("en_proceso", "En proceso"),
                            ("cerrada", "Cerrada"),
                        ],
                        default="pendiente",
                        max_length=15,
                    ),
                ),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                (
                    "participante",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="canalizaciones",
                        to="certificacion_intera.participante",
                    ),
                ),
            ],
            options={
                "verbose_name": "Canalización",
                "verbose_name_plural": "Canalizaciones",
                "ordering": ["-fecha", "-id"],
            },
        ),
        migrations.CreateModel(
            name="Consejeria",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("fecha", models.DateField()),
                ("observaciones", models.TextField()),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendiente", "Pendiente"),
                            ("realizada", "Realizada"),
                            ("cancelada", "Cancelada"),
                        ],
                        default="pendiente",
                        max_length=15,
                    ),
                ),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                (
                    "participante",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consejerias",
                        to="certificacion_intera.participante",
                    ),
                ),
            ],
            options={
                "verbose_name": "Consejería",
                "verbose_name_plural": "Consejerías",
                "ordering": ["fecha", "id"],
            },
        ),
        migrations.CreateModel(
            name="EntrevistaSeguimiento",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "nombre_confirmado",
                    models.CharField(max_length=200),
                ),
                (
                    "numero_alumno_confirmado",
                    models.CharField(max_length=50),
                ),
                ("fecha", models.DateField()),
                ("observaciones", models.TextField(blank=True)),
                (
                    "decision",
                    models.CharField(
                        choices=[
                            ("finalizar", "Finalizar caso"),
                            ("consejeria", "Enviar a consejería"),
                        ],
                        max_length=15,
                    ),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "participante",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entrevista",
                        to="certificacion_intera.participante",
                    ),
                ),
                (
                    "registrada_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Entrevista de seguimiento",
                "verbose_name_plural": "Entrevistas de seguimiento",
            },
        ),
        migrations.CreateModel(
            name="AplicacionInstrumento",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "token",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendiente", "Pendiente"),
                            ("respondida", "Respondida"),
                            ("cancelada", "Cancelada"),
                        ],
                        default="pendiente",
                        max_length=15,
                    ),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "respondido_en",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "puntaje_total",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=8,
                        null=True,
                    ),
                ),
                ("interpretacion", models.TextField(blank=True)),
                (
                    "resultado_detalle",
                    models.JSONField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "generado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "instrumento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="aplicaciones",
                        to="certificacion_intera.instrumento",
                    ),
                ),
                (
                    "participante",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="aplicaciones",
                        to="certificacion_intera.participante",
                    ),
                ),
                (
                    "proceso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="aplicaciones",
                        to="certificacion_intera.procesocertificacion",
                    ),
                ),
            ],
            options={
                "verbose_name": "Aplicación de instrumento",
                "verbose_name_plural": "Aplicaciones de instrumentos",
                "ordering": ["-creado_en"],
            },
        ),
        migrations.CreateModel(
            name="RespuestaInstrumento",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("valor", models.TextField(blank=True)),
                (
                    "valor_numerico",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=8,
                        null=True,
                    ),
                ),
                (
                    "aplicacion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="respuestas",
                        to="certificacion_intera.aplicacioninstrumento",
                    ),
                ),
                (
                    "pregunta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="respuestas",
                        to="certificacion_intera.preguntainstrumento",
                    ),
                ),
            ],
            options={
                "verbose_name": "Respuesta de instrumento",
                "verbose_name_plural": "Respuestas de instrumentos",
                "ordering": ["pregunta__orden"],
                "unique_together": {("aplicacion", "pregunta")},
            },
        ),
    ]