from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class RegistroAuditoria(models.Model):
    """Bitácora de cambios del portal (RF-19). Guarda quién hizo qué, cuándo,
    y con qué valores antes y después — el requisito de "mantener histórico de
    cambios: usuario, fecha, monto anterior, monto nuevo" de la sección 9 del
    documento de requerimientos financieros.

    Vive en `apps/core` y no en `apps/finanzas` a propósito: la van a
    necesitar los módulos que siguen (RH, clínico), igual que
    `permisos/grupos.py`. Finanzas solo la consume.

    Es un registro de solo-agregar: nada la edita ni la borra. Por eso los
    valores se guardan como texto ya formateado (no como FK ni Decimal): la
    bitácora debe seguir siendo legible aunque el registro original cambie de
    forma o desaparezca — de ahí también `descripcion_objeto`, que es una
    copia del `str()` del registro al momento del cambio."""

    class Accion(models.TextChoices):
        CREO = 'creo', 'Creó'
        MODIFICO = 'modifico', 'Modificó'
        SELLO = 'sello', 'Selló'
        AJUSTO = 'ajusto', 'Ajustó'
        IMPORTO = 'importo', 'Importó / sincronizó'
        ELIMINO = 'elimino', 'Eliminó'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='movimientos_auditoria',
    )
    fecha = models.DateTimeField(auto_now_add=True)
    # null=True: hay acciones que no son sobre un registro puntual (una
    # sincronización completa, por ejemplo). SET_NULL en content_type para
    # que borrar un modelo del sistema no se lleve la bitácora con él.
    content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    registro = GenericForeignKey('content_type', 'object_id')
    descripcion_objeto = models.CharField(max_length=255, blank=True)
    accion = models.CharField(max_length=20, choices=Accion.choices)
    campo = models.CharField(max_length=60, blank=True)
    valor_anterior = models.CharField(max_length=255, blank=True)
    valor_nuevo = models.CharField(max_length=255, blank=True)
    detalle = models.CharField(max_length=255, blank=True)

    class Meta:
        # El paquete `auditoria/` es organizativo, no una app Django aparte:
        # sin app_label explícito Django no sabría a qué app pertenece este
        # modelo (ver CLAUDE.md, `apps/core` es una sola app).
        app_label = 'core'
        verbose_name = 'Registro de auditoría'
        verbose_name_plural = 'Bitácora de auditoría'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['-fecha']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        quien = self.usuario or 'sistema'
        return f'{quien} {self.get_accion_display().lower()} {self.descripcion_objeto}'
