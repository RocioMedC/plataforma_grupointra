"""Punto único de entrada a la bitácora de auditoría.

Los módulos de negocio llaman `registrar(...)` y nunca instancian
`RegistroAuditoria` a mano, para que el día que la bitácora cambie de forma
(o se mande a otro destino) solo haya que tocar este archivo.
"""

import logging

from django.contrib.contenttypes.models import ContentType

from .models import RegistroAuditoria

logger = logging.getLogger(__name__)


def _texto(valor, limite=255):
    if valor is None or valor == '':
        return ''
    return str(valor)[:limite]


def _usuario_valido(usuario):
    # request.user puede ser AnonymousUser (o None si el llamado viene de un
    # comando o de una tarea), y un FK no acepta AnonymousUser.
    return usuario if getattr(usuario, 'is_authenticated', False) else None


def registrar(usuario, objeto, accion, campo='', anterior='', nuevo='', detalle=''):
    """Deja constancia de un cambio. `objeto` puede ser None cuando la acción
    no es sobre un registro puntual (por ejemplo, una sincronización).

    Nunca propaga excepciones: si la bitácora falla, se registra en el log
    pero la operación de negocio que la llamó debe seguir su curso — perder
    una línea de auditoría es malo, tumbar un sellado de nómina es peor.
    """
    try:
        datos = dict(
            usuario=_usuario_valido(usuario),
            accion=accion,
            campo=_texto(campo, 60),
            valor_anterior=_texto(anterior),
            valor_nuevo=_texto(nuevo),
            detalle=_texto(detalle),
        )
        if objeto is not None and objeto.pk is not None:
            datos.update(
                content_type=ContentType.objects.get_for_model(objeto),
                object_id=objeto.pk,
                descripcion_objeto=_texto(objeto),
            )
        elif detalle:
            datos['descripcion_objeto'] = _texto(detalle)
        return RegistroAuditoria.objects.create(**datos)
    except Exception:
        logger.exception('No se pudo escribir en la bitácora de auditoría (%s / %s).', accion, campo)
        return None


def registrar_cambio_de_campo(usuario, objeto, campo, anterior, nuevo, etiqueta=''):
    """Atajo para el caso más común: un campo que cambió de valor. Si el
    valor no cambió realmente, no ensucia la bitácora."""
    if str(anterior) == str(nuevo):
        return None
    return registrar(
        usuario, objeto, RegistroAuditoria.Accion.MODIFICO,
        campo=etiqueta or campo, anterior=anterior, nuevo=nuevo,
    )


def historial_de(objeto):
    """Bitácora de un registro puntual, del más reciente al más antiguo."""
    return RegistroAuditoria.objects.filter(
        content_type=ContentType.objects.get_for_model(objeto),
        object_id=objeto.pk,
    ).select_related('usuario')
