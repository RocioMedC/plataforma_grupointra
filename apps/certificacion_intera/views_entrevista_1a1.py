from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.portafolio.models import (
    Instrumento,
    PreguntaInstrumento,
)
from apps.portafolio.services_entrevista import (
    CLAVE_ENTREVISTA,
    publicar_revision,
)

from .models import (
    EntrevistaUnoAUno,
    RespuestaEntrevistaUnoAUno,
    VerificacionAccesoEntrevista,
)
from .services_entrevista_1a1 import (
    registrar,
    requisitos,
    verificar,
    visible,
)
from .views import (
    _participante,
    acceso_certificacion_intera_requerido,
)


def _permiso(usuario, nombre):
    return (
        usuario.is_superuser
        or usuario.has_perm(
            'certificacion_intera.' + nombre
        )
    )


def _requiere(usuario, nombre):
    if not _permiso(usuario, nombre):
        raise PermissionDenied


def _estructura(entrevista):
    estructura = entrevista.revision_plantilla.estructura

    respuestas = {
        r.pregunta.clave: r.valor
        for r in entrevista.respuestas.filter(
            revision=entrevista.revision_actual
        ).select_related('pregunta')
    }

    secciones = []
    preguntas_por_seccion = {}

    for pregunta in estructura.get('preguntas', []):
        preguntas_por_seccion.setdefault(
            pregunta.get('seccion'),
            [],
        ).append(pregunta)

    for seccion in estructura.get('secciones', []):
        preguntas = []

        for pregunta in preguntas_por_seccion.get(
            seccion.get('clave'),
            [],
        ):
            pregunta = {
                **pregunta,
                'tipo': pregunta['tipo_respuesta'],
                'visible': visible(
                    pregunta,
                    respuestas,
                ),
                'respuesta': respuestas.get(
                    pregunta['clave'],
                    '',
                ),
            }

            preguntas.append(pregunta)

        secciones.append(
            {
                **seccion,
                'preguntas': preguntas,
            }
        )

    return secciones, respuestas


@acceso_certificacion_intera_requerido
def acceso_view(request, participante_id):
    _requiere(
        request.user,
        'request_entrevista_1a1',
    )

    participante = _participante(participante_id)
    validacion = requisitos(participante)

    if request.method == 'POST':
        try:
            nacimiento = date.fromisoformat(
                request.POST.get(
                    'fecha_nacimiento',
                    '',
                )
            )
        except ValueError:
            nacimiento = None

        acceso = verificar(
            participante,
            request.user,
            request.POST.get(
                'nombre',
                '',
            ),
            nacimiento,
        )

        if acceso.exitosa:
            messages.success(
                request,
                'Identidad confirmada. Puedes iniciar la entrevista.',
            )

            return redirect(
                'certificacion_intera:entrevista_1a1',
                participante_id=participante.id,
            )

        messages.error(
            request,
            (
                'No fue posible validar la identidad o aún hay '
                'requisitos pendientes.'
            ),
        )

    return render(
        request,
        'certificacion_intera/entrevista_1a1_acceso.html',
        {
            'participante': participante,
            'validacion': validacion,
            'vista_actual': 'seguimiento',
        },
    )


@acceso_certificacion_intera_requerido
def entrevista_view(request, participante_id):
    participante = _participante(participante_id)

    _requiere(
        request.user,
        'manage_entrevista_1a1',
    )

    entrevista = (
        EntrevistaUnoAUno.objects
        .filter(
            participante=participante,
            proceso=participante.proceso,
        )
        .select_related('revision_plantilla')
        .first()
    )

    if not entrevista:
        acceso = (
            VerificacionAccesoEntrevista.objects
            .filter(
                participante=participante,
                usuaria=request.user,
                exitosa=True,
                usada_en__isnull=True,
                autorizada_hasta__gte=timezone.now(),
            )
            .order_by('-creada_en')
            .first()
        )

        if not acceso:
            return redirect(
                'certificacion_intera:entrevista_1a1_acceso',
                participante_id=participante.id,
            )

        instrumento = get_object_or_404(
            Instrumento,
            clave=CLAVE_ENTREVISTA,
            activo=True,
        )

        revision = publicar_revision(instrumento)

        entrevista = EntrevistaUnoAUno.objects.create(
            participante=participante,
            proceso=participante.proceso,
            instrumento=instrumento,
            revision_plantilla=revision,
            responsable=request.user,
            iniciada_por=request.user,
        )

        acceso.usada_en = timezone.now()

        acceso.save(
            update_fields=[
                'usada_en',
            ]
        )

        registrar(
            entrevista,
            'Entrevista iniciada',
            request.user,
        )

    secciones, valores = _estructura(entrevista)

    if request.method == 'POST':
        finalizar = (
            request.POST.get('accion')
            == 'finalizar'
        )

        if finalizar:
            _requiere(
                request.user,
                'finish_entrevista_1a1',
            )

        if (
            entrevista.estado
            == EntrevistaUnoAUno.Estado.FINALIZADA
        ):
            raise PermissionDenied

        faltantes = []

        preguntas_modelo = {
            p.clave: p
            for p in PreguntaInstrumento.objects.filter(
                instrumento=entrevista.instrumento
            )
        }

        preguntas_plantilla = (
            entrevista.revision_plantilla
            .estructura
            .get(
                'preguntas',
                [],
            )
        )

        valores_enviados = {
            pregunta['clave']: request.POST.get(
                'pregunta_' + pregunta['clave'],
                '',
            ).strip()
            for pregunta in preguntas_plantilla
        }

        with transaction.atomic():
            for pregunta in preguntas_plantilla:
                clave = pregunta['clave']

                if not visible(
                    pregunta,
                    valores_enviados,
                ):
                    RespuestaEntrevistaUnoAUno.objects.filter(
                        entrevista=entrevista,
                        pregunta=preguntas_modelo[clave],
                        revision=entrevista.revision_actual,
                    ).delete()

                    continue

                valor = valores_enviados[clave]

                if (
                    finalizar
                    and pregunta.get('requerida')
                    and not valor
                ):
                    faltantes.append(clave)
                    continue

                if (
                    clave == 'MOT-04'
                    and valor
                    and (
                        not valor.isdigit()
                        or not 1 <= int(valor) <= 10
                    )
                ):
                    faltantes.append(clave)
                    continue

                RespuestaEntrevistaUnoAUno.objects.update_or_create(
                    entrevista=entrevista,
                    pregunta=preguntas_modelo[clave],
                    revision=entrevista.revision_actual,
                    defaults={
                        'valor': valor,
                        'valor_numerico': (
                            int(valor)
                            if clave == 'MOT-04' and valor
                            else None
                        ),
                    },
                )

            if faltantes:
                messages.error(
                    request,
                    (
                        'Completa las preguntas obligatorias visibles '
                        'antes de finalizar.'
                    ),
                )

            elif finalizar:
                entrevista.estado = (
                    EntrevistaUnoAUno.Estado.FINALIZADA
                )
                entrevista.finalizada_por = request.user
                entrevista.finalizada_en = timezone.now()
                entrevista.save()

                registrar(
                    entrevista,
                    'Entrevista finalizada',
                    request.user,
                )

                messages.success(
                    request,
                    'Entrevista finalizada.',
                )

                return redirect(
                    'certificacion_intera:entrevista_1a1',
                    participante_id=participante.id,
                )

            else:
                entrevista.save(
                    update_fields=[
                        'actualizada_en',
                    ]
                )

                registrar(
                    entrevista,
                    'Borrador guardado',
                    request.user,
                )

                messages.success(
                    request,
                    'Borrador guardado.',
                )

                return redirect(
                    'certificacion_intera:entrevista_1a1',
                    participante_id=participante.id,
                )

        secciones, valores = _estructura(entrevista)

    return render(
        request,
        'certificacion_intera/entrevista_1a1.html',
        {
            'participante': participante,
            'entrevista': entrevista,
            'secciones': secciones,
            'puede_finalizar': _permiso(
                request.user,
                'finish_entrevista_1a1',
            ),
            'puede_reabrir': _permiso(
                request.user,
                'reopen_entrevista_1a1',
            ),
            'puede_historial': _permiso(
                request.user,
                'view_historial_entrevista_1a1',
            ),
            'vista_actual': 'seguimiento',
        },
    )


@acceso_certificacion_intera_requerido
def reabrir_view(request, participante_id):
    _requiere(
        request.user,
        'reopen_entrevista_1a1',
    )

    participante = _participante(participante_id)

    entrevista = get_object_or_404(
        EntrevistaUnoAUno,
        participante=participante,
        proceso=participante.proceso,
    )

    justificacion = request.POST.get(
        'justificacion',
        '',
    ).strip()

    if (
        request.method != 'POST'
        or entrevista.estado
        != EntrevistaUnoAUno.Estado.FINALIZADA
        or not justificacion
    ):
        raise PermissionDenied

    with transaction.atomic():
        anterior = list(
            entrevista.respuestas.filter(
                revision=entrevista.revision_actual
            )
        )

        entrevista.revision_actual += 1
        entrevista.estado = (
            EntrevistaUnoAUno.Estado.REABIERTA
        )
        entrevista.reabierta_en = timezone.now()
        entrevista.justificacion_reapertura = justificacion
        entrevista.save()

        RespuestaEntrevistaUnoAUno.objects.bulk_create(
            [
                RespuestaEntrevistaUnoAUno(
                    entrevista=entrevista,
                    pregunta=r.pregunta,
                    revision=entrevista.revision_actual,
                    valor=r.valor,
                    valor_numerico=r.valor_numerico,
                    valor_fecha=r.valor_fecha,
                )
                for r in anterior
            ]
        )

        registrar(
            entrevista,
            'Entrevista reabierta',
            request.user,
            justificacion=justificacion,
        )

    messages.success(
        request,
        'Entrevista reabierta en una nueva revisión.',
    )

    return redirect(
        'certificacion_intera:entrevista_1a1',
        participante_id=participante.id,
    )