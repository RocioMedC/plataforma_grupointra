import unicodedata
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.portafolio.services_entrevista import (
    CLAVE_ENTREVISTA,
    publicar_revision,
)

from .models import (
    AplicacionInstrumento,
    EntrevistaUnoAUno,
    HistorialEntrevistaUnoAUno,
    RespuestaEntrevistaUnoAUno,
    VerificacionAccesoEntrevista,
)


def normalizar(texto):
    return ' '.join(
        unicodedata.normalize(
            'NFKD',
            texto or '',
        )
        .encode(
            'ascii',
            'ignore',
        )
        .decode()
        .casefold()
        .split()
    )


def requisitos(participante):
    configuraciones = (
        participante.proceso.configuraciones_instrumento
        .filter(requerido=True)
        .select_related('instrumento')
    )

    pendientes = []
    faltantes = []

    for configuracion in configuraciones:
        aplicacion = participante.aplicaciones.filter(
            instrumento=configuracion.instrumento
        ).first()

        if (
            not aplicacion
            or aplicacion.estado
            != AplicacionInstrumento.Estado.RESPONDIDA
        ):
            pendientes.append(
                configuracion.instrumento.nombre
            )
            continue

        faltantes += [
            p.clave or str(p.id)
            for p in configuracion.instrumento.preguntas.filter(
                requerida=True
            )
            if not aplicacion.respuestas.filter(
                pregunta=p
            ).exclude(
                valor=''
            ).exists()
        ]

    datos = []

    if not participante.fecha_nacimiento:
        datos.append('fecha de nacimiento')

    return {
        'puede_iniciar': (
            not pendientes
            and not faltantes
            and not datos
        ),
        'instrumentos_pendientes': pendientes,
        'respuestas_pendientes': faltantes,
        'datos_faltantes': datos,
    }


def registrar(
    entrevista,
    event,
    usuario,
    descripcion='',
    justificacion='',
):
    HistorialEntrevistaUnoAUno.objects.create(
        entrevista=entrevista,
        evento=event,
        usuario=usuario,
        revision=entrevista.revision_actual,
        descripcion=descripcion,
        justificacion=justificacion,
    )

    from .models import BitacoraProceso

    BitacoraProceso.objects.create(
        proceso=entrevista.proceso,
        evento=f'Entrevista 1:1 · {event}',
        descripcion='Evento administrativo de entrevista.',
        usuario=usuario,
    )


def verificar(
    participante,
    usuario,
    numero,
    nombre,
    fecha,
):
    ventana = timezone.now() - timedelta(
        minutes=int(
            getattr(
                settings,
                'ENTREVISTA_1A1_VENTANA_INTENTOS_MINUTOS',
                15,
            )
        )
    )

    limite = int(
        getattr(
            settings,
            'ENTREVISTA_1A1_MAX_INTENTOS',
            5,
        )
    )

    intentos = VerificacionAccesoEntrevista.objects.filter(
        participante=participante,
        usuaria=usuario,
        creada_en__gte=ventana,
        exitosa=False,
    ).count()

    ok = (
        intentos < limite
        and requisitos(participante)['puede_iniciar']
        and normalizar(numero)
        == normalizar(participante.numero_alumno)
        and normalizar(nombre)
        == normalizar(participante.nombre)
        and fecha == participante.fecha_nacimiento
    )

    hasta = (
        timezone.now()
        + timedelta(
            minutes=int(
                getattr(
                    settings,
                    'ENTREVISTA_1A1_AUTORIZACION_MINUTOS',
                    15,
                )
            )
        )
        if ok
        else None
    )

    acceso = VerificacionAccesoEntrevista.objects.create(
        participante=participante,
        proceso=participante.proceso,
        usuaria=usuario,
        exitosa=ok,
        autorizada_hasta=hasta,
    )

    return acceso


def visible(pregunta, valores):
    condicion = pregunta.get('condicion_visibilidad')

    return (
        not condicion
        or valores.get(
            condicion['pregunta_clave']
        ) == condicion['valor']
    )