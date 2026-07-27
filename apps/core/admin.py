from django.contrib import admin

from .auditoria.models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Solo lectura, incluso para superusuarios: una bitácora que se puede
    editar o borrar desde el admin deja de servir como bitácora."""

    list_display = ('fecha', 'usuario', 'accion', 'descripcion_objeto', 'campo', 'valor_anterior', 'valor_nuevo')
    list_filter = ('accion', 'content_type', 'fecha')
    search_fields = ('descripcion_objeto', 'detalle', 'usuario__username')
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
