from django.contrib import admin

from .models import (
    AplicacionInstrumento,
    Canalizacion,
    ConfiguracionInstrumento,
    Consejeria,
    Escuela,
    EntrevistaSeguimiento,
    EntrevistaUnoAUno,
    HistorialEntrevistaUnoAUno,
    Participante,
    ProcesoCertificacion,
    RespuestaInstrumento,
    SolicitudAtencion,
    VerificacionAccesoEntrevista,
)


@admin.register(Escuela)
class EscuelaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "director",
        "cantidad_total_alumnos",
        "estado",
        "municipio",
    )

    search_fields = (
        "nombre",
        "director",
        "contacto",
        "municipio",
    )


@admin.register(ProcesoCertificacion)
class ProcesoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "escuela",
        "estado",
        "fecha_inicio",
        "fecha_cierre",
    )

    list_filter = (
        "estado",
    )

    search_fields = (
        "nombre",
        "escuela__nombre",
    )


@admin.register(AplicacionInstrumento)
class AplicacionAdmin(admin.ModelAdmin):
    list_display = (
        "instrumento",
        "participante",
        "estado",
        "creado_en",
        "respondido_en",
    )

    list_filter = (
        "estado",
        "instrumento",
    )

    search_fields = (
        "participante__nombre",
        "participante__numero_alumno",
    )


admin.site.register(
    (
        ConfiguracionInstrumento,
        Participante,
        RespuestaInstrumento,
        EntrevistaSeguimiento,
        Consejeria,
        EntrevistaUnoAUno,
        HistorialEntrevistaUnoAUno,
        VerificacionAccesoEntrevista,
    )
)


@admin.register(Canalizacion)
class CanalizacionAdmin(admin.ModelAdmin):
    list_display = (
        "participante",
        "tipo",
        "estado",
        "prioridad",
        "destino",
        "fecha",
        "estado_envio",
    )

    list_filter = (
        "tipo",
        "estado",
        "prioridad",
        "estado_envio",
        "estado_clinico",
    )

    search_fields = (
        "participante__nombre",
        "participante__numero_alumno",
        "motivo",
        "remoto_id",
    )


@admin.register(SolicitudAtencion)
class SolicitudAtencionAdmin(admin.ModelAdmin):
    list_display = (
        "canalizacion",
        "integration_status",
        "remote_status",
        "send_attempts",
        "sent_at",
    )

    list_filter = (
        "integration_status",
        "remote_status",
    )

    search_fields = (
        "canalizacion__participante__nombre",
        "external_request_id",
    )