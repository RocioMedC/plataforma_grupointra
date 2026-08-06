from pathlib import Path

from django.conf import settings
from django.db import models


class CategoriaDocumento(models.Model):
    nombre = models.CharField(
        max_length=100,
        unique=True,
    )
    descripcion = models.TextField(
        blank=True,
    )
    activa = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = [
            'nombre',
        ]
        verbose_name = 'Categoría de documento'
        verbose_name_plural = 'Categorías de documentos'

    def __str__(self):
        return self.nombre


class Instrumento(models.Model):
    nombre = models.CharField(
        max_length=150,
    )
    clave = models.SlugField(
        max_length=50,
        unique=True,
    )
    descripcion = models.TextField(
        blank=True,
    )
    instrucciones = models.TextField(
        blank=True,
    )
    documento_origen = models.ForeignKey(
        'Documento',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='instrumentos_origen',
    )
    activo = models.BooleanField(
        default=True,
    )
    version = models.CharField(
        max_length=30,
        default='1.0',
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            'nombre',
        ]
        verbose_name = 'Instrumento'
        verbose_name_plural = 'Instrumentos'

    def __str__(self):
        return self.nombre


class PreguntaInstrumento(models.Model):
    class Tipo(models.TextChoices):
        OPCION_UNICA = (
            'opcion_unica',
            'Opción única',
        )
        OPCION_MULTIPLE = (
            'opcion_multiple',
            'Opción múltiple',
        )
        ESCALA = (
            'escala',
            'Escala Likert',
        )
        SI_NO = (
            'si_no',
            'Sí / No',
        )
        TEXTO_LIBRE = (
            'texto_libre',
            'Texto libre',
        )
        TEXTO_CORTO = (
            'texto_corto',
            'Texto corto',
        )
        FECHA = (
            'fecha',
            'Fecha',
        )

    instrumento = models.ForeignKey(
        Instrumento,
        on_delete=models.CASCADE,
        related_name='preguntas',
    )
    orden = models.PositiveIntegerField(
        default=0,
    )
    texto = models.TextField()
    clave = models.CharField(
        max_length=50,
        blank=True,
    )
    tipo_respuesta = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.OPCION_UNICA,
    )
    opciones = models.JSONField(
        blank=True,
        null=True,
        help_text='Lista de objetos {valor, etiqueta}.',
    )
    requerida = models.BooleanField(
        default=True,
    )
    seccion = models.ForeignKey(
        'SeccionInstrumento',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='preguntas',
    )
    condicion_visibilidad = models.JSONField(
        blank=True,
        null=True,
        help_text=(
            '{"pregunta_clave": "MOT-02", '
            '"operador": "igual", "valor": "si"}.'
        ),
    )

    class Meta:
        ordering = [
            'instrumento',
            'orden',
            'id',
        ]
        verbose_name = 'Pregunta de instrumento'
        verbose_name_plural = 'Preguntas de instrumentos'

    def __str__(self):
        return f'{self.instrumento} #{self.orden}'


class SeccionInstrumento(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = (
            'activa',
            'Activa',
        )
        INACTIVA = (
            'inactiva',
            'Inactiva',
        )

    instrumento = models.ForeignKey(
        Instrumento,
        on_delete=models.CASCADE,
        related_name='secciones',
    )
    clave = models.CharField(
        max_length=50,
    )
    nombre = models.CharField(
        max_length=150,
    )
    descripcion = models.TextField(
        blank=True,
    )
    orden = models.PositiveIntegerField(
        default=0,
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVA,
    )

    class Meta:
        ordering = [
            'instrumento',
            'orden',
            'id',
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'instrumento',
                    'clave',
                ],
                name='seccion_clave_unica_por_instrumento',
            ),
        ]

    def __str__(self):
        return f'{self.instrumento} · {self.nombre}'


class RevisionInstrumento(models.Model):
    class Estado(models.TextChoices):
        PUBLICADA = (
            'publicada',
            'Publicada',
        )
        ARCHIVADA = (
            'archivada',
            'Archivada',
        )

    instrumento = models.ForeignKey(
        Instrumento,
        on_delete=models.PROTECT,
        related_name='revisiones',
    )
    version = models.CharField(
        max_length=30,
    )
    estructura = models.JSONField()
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.PUBLICADA,
    )
    publicada_en = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            '-publicada_en',
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'instrumento',
                    'version',
                ],
                name='revision_unica_por_instrumento_y_version',
            ),
        ]

    def __str__(self):
        return f'{self.instrumento} v{self.version}'


class CalculadoraInstrumento(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = (
            'activa',
            'Activa',
        )
        ORIENTATIVA = (
            'orientativa',
            'Orientativa',
        )
        BLOQUEADA = (
            'bloqueada',
            'Bloqueada',
        )
        NO_DIAGNOSTICA = (
            'no_diagnostica',
            'No diagnóstica',
        )

    instrumento = models.ForeignKey(
        Instrumento,
        on_delete=models.PROTECT,
        related_name='calculadoras',
    )
    clave = models.SlugField(
        max_length=80,
    )
    version_regla = models.CharField(
        max_length=30,
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
    )
    definicion = models.JSONField(
        default=dict,
    )
    huella_contenido = models.CharField(
        max_length=64,
    )
    creada_en = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'instrumento',
                    'clave',
                    'version_regla',
                ],
                name='calculadora_unica_por_version',
            ),
        ]

    def __str__(self):
        return (
            f'{self.instrumento} · '
            f'{self.clave} v{self.version_regla}'
        )


class ImportacionInstrumento(models.Model):
    instrumento = models.OneToOneField(
        Instrumento,
        on_delete=models.CASCADE,
        related_name='importacion',
    )
    documento = models.ForeignKey(
        'Documento',
        on_delete=models.PROTECT,
        related_name='importaciones_instrumento',
    )
    huella_contenido = models.CharField(
        max_length=64,
        db_index=True,
    )
    metadatos = models.JSONField(
        default=dict,
        blank=True,
    )
    creada_en = models.DateTimeField(
        auto_now_add=True,
    )


class Documento(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = (
            'activo',
            'Activo',
        )
        INACTIVO = (
            'inactivo',
            'Inactivo',
        )

    nombre = models.CharField(
        max_length=200,
    )
    archivo = models.FileField(
        upload_to='portafolio/documentos/',
    )
    categoria = models.ForeignKey(
        CategoriaDocumento,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='documentos',
    )
    tipo_archivo = models.CharField(
        max_length=30,
        blank=True,
        editable=False,
    )
    descripcion = models.TextField(
        blank=True,
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVO,
    )
    version = models.CharField(
        max_length=30,
        default='1.0',
    )
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='documentos_portafolio',
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
    )
    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            '-creado_en',
        ]
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if self.archivo:
            self.tipo_archivo = (
                Path(self.archivo.name)
                .suffix
                .lower()
                .lstrip('.')
            )

        super().save(*args, **kwargs)


class PlantillaPDF(models.Model):
    nombre = models.CharField(
        max_length=200,
    )
    descripcion = models.TextField(
        blank=True,
    )
    archivo = models.FileField(
        upload_to='portafolio/plantillas_pdf/',
    )
    documento_origen = models.ForeignKey(
        Documento,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='plantillas_pdf',
    )
    activa = models.BooleanField(
        default=True,
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            'nombre',
        ]
        verbose_name = 'Plantilla PDF'
        verbose_name_plural = 'Plantillas PDF'

    def __str__(self):
        return self.nombre


class Reporte(models.Model):
    nombre = models.CharField(
        max_length=200,
    )
    clave = models.SlugField(
        max_length=50,
        unique=True,
    )
    descripcion = models.TextField(
        blank=True,
    )
    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = [
            'nombre',
        ]
        verbose_name = 'Reporte'
        verbose_name_plural = 'Reportes'

    def __str__(self):
        return self.nombre


class RecursoCompartido(models.Model):
    nombre = models.CharField(
        max_length=200,
    )
    tipo = models.CharField(
        max_length=100,
        blank=True,
    )
    descripcion = models.TextField(
        blank=True,
    )
    archivo = models.FileField(
        upload_to='portafolio/recursos/',
    )
    documento_origen = models.ForeignKey(
        Documento,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='recursos_compartidos',
    )
    activo = models.BooleanField(
        default=True,
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            'nombre',
        ]
        verbose_name = 'Recurso compartido'
        verbose_name_plural = 'Recursos compartidos'

    def __str__(self):
        return self.nombre