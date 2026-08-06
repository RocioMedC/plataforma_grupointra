from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from .consultorio_web import (
    ConsultorioWebError,
    consultar_estado,
    enviar_solicitud,
    payload_for,
    validar_configuracion,
)
from .forms import CanalizacionForm
from .models import (
    AplicacionInstrumento,
    BitacoraProceso,
    Canalizacion,
    Participante,
    ProcesoCertificacion,
    SolicitudAtencion,
)
from .services import obtener_aplicacion_publica
from .views import acceso_certificacion_intera_requerido


REMOTE_STATUS_LABELS = {
    'recibida': 'Recibida',
    'en_revision': 'En revisión',
    'informacion_incompleta': 'Información incompleta',
    'paciente_vinculado': 'Paciente vinculado',
    'paciente_registrado': 'Paciente registrado',
    'contacto_realizado': 'Contacto realizado',
    'cita_programada': 'Cita programada',
    'en_atencion': 'En atención',
    'finalizada': 'Finalizada',
    'rechazada': 'Rechazada',
    'cancelada': 'Cancelada',
}


@acceso_certificacion_intera_requerido
def proceso_bitacora_view(request, proceso_id):
    proceso = get_object_or_404(
        ProcesoCertificacion,
        id=proceso_id,
    )

    return render(
        request,
        'certificacion_intera/bitacora.html',
        {
            'vista_actual': 'procesos',
            'proceso': proceso,
            'eventos': proceso.bitacora.select_related('usuario'),
        },
    )


@acceso_certificacion_intera_requerido
def proceso_aplicaciones_publicas_view(request, proceso_id):
    proceso = get_object_or_404(
        ProcesoCertificacion,
        id=proceso_id,
    )
    tarjetas = []

    for configuracion in proceso.configuraciones_instrumento.select_related(
        'instrumento'
    ):
        publica, _ = obtener_aplicacion_publica(
            configuracion,
            request.user,
        )
        aplicaciones = proceso.aplicaciones.filter(
            instrumento=configuracion.instrumento
        )

        tarjetas.append(
            {
                'configuracion': configuracion,
                'preguntas': configuracion.instrumento.preguntas.count(),
                'url': request.build_absolute_uri(publica.url_publica),
                'participantes': aplicaciones.values(
                    'participante_id'
                ).distinct().count(),
                'respondidos': aplicaciones.filter(
                    estado=AplicacionInstrumento.Estado.RESPONDIDA
                ).count(),
                'pendientes': aplicaciones.filter(
                    estado=AplicacionInstrumento.Estado.PENDIENTE
                ).count(),
            }
        )

    return render(
        request,
        'certificacion_intera/aplicaciones_publicas.html',
        {
            'vista_actual': 'procesos',
            'proceso': proceso,
            'tarjetas': tarjetas,
        },
    )


@acceso_certificacion_intera_requerido
def canalizacion_crear_view(request, participante_id):
    participante = get_object_or_404(
        Participante.objects.select_related('proceso'),
        id=participante_id,
    )
    form = CanalizacionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        canalizacion = form.save(commit=False)
        canalizacion.participante = participante
        canalizacion.registrada_por = request.user

        try:
            canalizacion.save()
            SolicitudAtencion.objects.create(
                canalizacion=canalizacion,
                creada_por=request.user,
            )
        except Exception as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request,
                'Canalización registrada y pendiente de envío.',
            )
            return redirect(
                'certificacion_intera:canalizacion_detalle',
                canalizacion_id=canalizacion.id,
            )

    return render(
        request,
        'certificacion_intera/form.html',
        {
            'vista_actual': 'canalizaciones',
            'form': form,
            'titulo_formulario': 'Registrar canalización',
            'volver_url': reverse(
                'certificacion_intera:participante_detalle',
                args=[participante.id],
            ),
        },
    )


def _integration_event(solicitud, event, message, user):
    BitacoraProceso.objects.create(
        proceso=solicitud.canalizacion.participante.proceso,
        evento=event,
        descripcion=message,
        usuario=user,
    )


def _send_readiness(solicitud):
    """Valida localmente el contrato sin enviar datos ni abrir conexiones HTTP."""

    try:
        validar_configuracion()
        payload_for(solicitud)
    except ConsultorioWebError as exc:
        return exc.message

    return ''


@acceso_certificacion_intera_requerido
def canalizacion_detalle_view(request, canalizacion_id):
    canalizacion = get_object_or_404(
        Canalizacion.objects.select_related(
            'participante__proceso__escuela',
            'registrada_por',
        ),
        id=canalizacion_id,
    )
    solicitud = getattr(
        canalizacion,
        'solicitud_atencion',
        None,
    )
    eventos = canalizacion.participante.proceso.bitacora.filter(
        descripcion__contains=canalizacion.participante.nombre
    )[:20]
    readiness_error = _send_readiness(solicitud) if solicitud else ''

    return render(
        request,
        'certificacion_intera/canalizacion_detalle.html',
        {
            'vista_actual': 'canalizaciones',
            'canalizacion': canalizacion,
            'solicitud': solicitud,
            'eventos': eventos,
            'readiness_error': readiness_error,
            'remote_status_label': (
                REMOTE_STATUS_LABELS.get(
                    solicitud.remote_status,
                    solicitud.remote_status,
                )
                if solicitud
                else ''
            ),
            'integration_enabled': (
                settings.CONSULTORIOWEB_INTEGRATION_ENABLED
            ),
        },
    )


@acceso_certificacion_intera_requerido
def solicitud_confirmar_envio_view(request, canalizacion_id):
    canalizacion = get_object_or_404(
        Canalizacion.objects.select_related(
            'participante__proceso__escuela'
        ),
        id=canalizacion_id,
    )
    solicitud = get_object_or_404(
        SolicitudAtencion,
        canalizacion=canalizacion,
    )
    readiness_error = _send_readiness(solicitud)

    if (
        solicitud.integration_status
        == SolicitudAtencion.EstadoIntegracion.ENVIADA
    ):
        messages.info(
            request,
            'La solicitud ya fue enviada a Consultorio Web.',
        )
        return redirect(
            'certificacion_intera:canalizacion_detalle',
            canalizacion_id=canalizacion.id,
        )

    return render(
        request,
        'certificacion_intera/solicitud_confirmar_envio.html',
        {
            'vista_actual': 'canalizaciones',
            'canalizacion': canalizacion,
            'solicitud': solicitud,
            'readiness_error': readiness_error,
        },
    )


def _http_error_event(status):
    return {
        400: 'Error de contrato',
        401: 'Error de autenticación',
        403: 'Error de autenticación',
        409: 'Conflicto de idempotencia',
        422: 'Error de contrato',
        429: 'Error de comunicación',
    }.get(
        status,
        'Error de comunicación',
    )


@acceso_certificacion_intera_requerido
@require_POST
def solicitud_enviar_view(request, canalizacion_id):
    canalizacion = get_object_or_404(
        Canalizacion.objects.select_related(
            'participante__proceso__escuela'
        ),
        id=canalizacion_id,
    )
    solicitud = get_object_or_404(
        SolicitudAtencion,
        canalizacion=canalizacion,
    )

    if (
        solicitud.integration_status
        == SolicitudAtencion.EstadoIntegracion.ENVIADA
    ):
        messages.info(
            request,
            'La solicitud ya fue enviada a Consultorio Web.',
        )
        return redirect(
            'certificacion_intera:canalizacion_detalle',
            canalizacion_id=canalizacion.id,
        )

    if request.POST.get('confirmar_envio') != 'si':
        messages.error(
            request,
            (
                'Confirma la autorización para compartir los datos '
                'administrativos.'
            ),
        )
        return redirect(
            'certificacion_intera:solicitud_confirmar_envio',
            canalizacion_id=canalizacion.id,
        )

    readiness_error = _send_readiness(solicitud)

    if readiness_error:
        messages.error(
            request,
            readiness_error,
        )
        return redirect(
            'certificacion_intera:solicitud_confirmar_envio',
            canalizacion_id=canalizacion.id,
        )

    _integration_event(
        solicitud,
        'Preparación del envío',
        'Información administrativa validada para envío.',
        request.user,
    )
    solicitud.integration_status = (
        SolicitudAtencion.EstadoIntegracion.ENVIANDO
    )
    solicitud.send_attempts += 1
    solicitud.last_send_attempt_at = timezone.now()
    solicitud.save(
        update_fields=[
            'integration_status',
            'send_attempts',
            'last_send_attempt_at',
            'actualizado_en',
        ]
    )
    _integration_event(
        solicitud,
        'Envío a Consultorio Web iniciado',
        'Solicitud preparada para envío.',
        request.user,
    )

    try:
        status, body = enviar_solicitud(solicitud)
    except ConsultorioWebError as exc:
        solicitud.integration_status = (
            SolicitudAtencion.EstadoIntegracion.ERROR
        )
        solicitud.last_error_code = exc.code
        solicitud.last_error_message = exc.message
        solicitud.save()

        _integration_event(
            solicitud,
            'Error de comunicación',
            exc.message,
            request.user,
        )
        messages.error(
            request,
            exc.message,
        )
    else:
        solicitud.last_response_at = timezone.now()

        if status in (200, 201):
            solicitud.integration_status = (
                SolicitudAtencion.EstadoIntegracion.ENVIADA
            )
            solicitud.estado = SolicitudAtencion.Estado.ENVIADA
            solicitud.remote_status = body.get(
                'status',
                'recibida',
            )
            solicitud.comentarios_recepcion = body.get(
                'message',
                '',
            )
            solicitud.remote_internal_request_id = body.get(
                'internal_request_id',
                '',
            )
            solicitud.remoto_id = solicitud.remote_internal_request_id
            solicitud.sent_at = solicitud.sent_at or timezone.now()
            solicitud.fecha_envio = solicitud.sent_at
            solicitud.last_error_code = ''
            solicitud.last_error_message = ''
            solicitud.save()

            event = (
                'Envío exitoso 201'
                if status == 201
                else 'Reintento idempotente exitoso 200'
            )

            _integration_event(
                solicitud,
                event,
                'Consultorio Web aceptó la solicitud.',
                request.user,
            )
            messages.success(
                request,
                'Solicitud enviada a Consultorio Web.',
            )
        else:
            solicitud.integration_status = (
                SolicitudAtencion.EstadoIntegracion.ERROR
            )
            solicitud.last_error_code = str(status)
            solicitud.last_error_message = body.get(
                'message',
                'Error administrativo de Consultorio Web.',
            )
            solicitud.save()

            _integration_event(
                solicitud,
                _http_error_event(status),
                f'Código HTTP {status}.',
                request.user,
            )
            messages.error(
                request,
                'No fue posible enviar la solicitud.',
            )

    return redirect(
        'certificacion_intera:canalizacion_detalle',
        canalizacion_id=canalizacion.id,
    )


@acceso_certificacion_intera_requerido
@require_POST
def solicitud_actualizar_estado_view(request, canalizacion_id):
    solicitud = get_object_or_404(
        SolicitudAtencion,
        canalizacion_id=canalizacion_id,
    )

    if (
        solicitud.integration_status
        != SolicitudAtencion.EstadoIntegracion.ENVIADA
    ):
        messages.error(
            request,
            'La solicitud aún no tiene un envío aceptado.',
        )
        return redirect(
            'certificacion_intera:canalizacion_detalle',
            canalizacion_id=canalizacion_id,
        )

    try:
        status, body = consultar_estado(solicitud)
    except ConsultorioWebError as exc:
        solicitud.last_error_code = exc.code
        solicitud.last_error_message = exc.message
        solicitud.last_status_check_at = timezone.now()
        solicitud.save()

        _integration_event(
            solicitud,
            'Error al consultar estado',
            exc.message,
            request.user,
        )
        messages.error(
            request,
            exc.message,
        )
    else:
        solicitud.last_status_check_at = timezone.now()
        solicitud.last_response_at = timezone.now()

        if status == 200:
            old_status = solicitud.remote_status
            remote_status = body.get(
                'status',
                '',
            )
            solicitud.remote_status = remote_status
            solicitud.comentarios_recepcion = body.get(
                'message',
                '',
            )
            remote_updated = body.get('updated_at')
            solicitud.remote_updated_at = (
                parse_datetime(remote_updated)
                if remote_updated
                else None
            )
            solicitud.last_error_code = ''
            solicitud.last_error_message = ''
            solicitud.save()

            if old_status != remote_status:
                _integration_event(
                    solicitud,
                    'Cambio de estado remoto',
                    REMOTE_STATUS_LABELS.get(
                        remote_status,
                        remote_status,
                    ),
                    request.user,
                )

                if remote_status == 'rechazada':
                    _integration_event(
                        solicitud,
                        'Solicitud remota rechazada',
                        'Consultorio Web rechazó la solicitud.',
                        request.user,
                    )
                elif remote_status == 'cancelada':
                    _integration_event(
                        solicitud,
                        'Solicitud remota cancelada',
                        'Consultorio Web canceló la solicitud.',
                        request.user,
                    )
            else:
                _integration_event(
                    solicitud,
                    'Estado remoto sin cambios',
                    (
                        'Consultorio Web confirmó el mismo estado '
                        'administrativo.'
                    ),
                    request.user,
                )

            _integration_event(
                solicitud,
                'Consulta de estado',
                'Consulta administrativa completada.',
                request.user,
            )
            messages.success(
                request,
                'Estado administrativo actualizado.',
            )
        else:
            solicitud.last_error_code = str(status)
            solicitud.last_error_message = body.get(
                'message',
                'Solicitud no localizada.',
            )
            solicitud.save()

            _integration_event(
                solicitud,
                _http_error_event(status),
                f'Código HTTP {status}.',
                request.user,
            )
            messages.error(
                request,
                'Consultorio Web no localizó la solicitud.',
            )

    return redirect(
        'certificacion_intera:canalizacion_detalle',
        canalizacion_id=canalizacion_id,
    )


@acceso_certificacion_intera_requerido
def canalizacion_editar_view(request, canalizacion_id):
    canalizacion = get_object_or_404(
        Canalizacion,
        id=canalizacion_id,
    )
    form = CanalizacionForm(
        request.POST or None,
        instance=canalizacion,
    )

    if request.method == 'POST' and form.is_valid():
        actualizada = form.save(commit=False)
        actualizada.registrada_por = request.user
        actualizada.save()

        messages.success(
            request,
            'Canalización actualizada.',
        )
        return redirect(
            'certificacion_intera:canalizacion_detalle',
            canalizacion_id=canalizacion.id,
        )

    return render(
        request,
        'certificacion_intera/form.html',
        {
            'vista_actual': 'canalizaciones',
            'form': form,
            'titulo_formulario': 'Editar canalización',
            'volver_url': reverse(
                'certificacion_intera:canalizacion_detalle',
                args=[canalizacion.id],
            ),
        },
    )