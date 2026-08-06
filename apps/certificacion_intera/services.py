from .models import (
    AplicacionPublica,
    BitacoraProceso,
)


def proceso_es_editable(proceso):
    """Centraliza el modo consulta de los procesos cerrados."""

    return proceso.estado != proceso.Estado.CERRADO


def obtener_aplicacion_publica(
    configuracion,
    usuario=None,
):
    """Obtiene el enlace publico unico de una configuracion y lo repara si falta."""

    aplicacion_publica, creada = (
        AplicacionPublica.objects.get_or_create(
            configuracion=configuracion
        )
    )

    if creada:
        BitacoraProceso.objects.create(
            proceso=configuracion.proceso,
            evento='Aplicacion publica generada',
            descripcion=configuracion.instrumento.nombre,
            usuario=(
                usuario
                if getattr(usuario, 'is_authenticated', False)
                else None
            ),
        )

    return aplicacion_publica, creada


def obtener_aplicacion_publica_proceso(
    proceso,
    usuario=None,
):
    """Obtiene el único enlace público general de la batería de un proceso."""

    aplicacion_publica, creada = (
        AplicacionPublica.objects.get_or_create(
            proceso=proceso
        )
    )

    if creada:
        BitacoraProceso.objects.create(
            proceso=proceso,
            evento='Aplicación pública general generada',
            descripcion='Enlace de batería pública creado.',
            usuario=(
                usuario
                if getattr(usuario, 'is_authenticated', False)
                else None
            ),
        )

    return aplicacion_publica, creada