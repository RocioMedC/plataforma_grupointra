"""Cliente HTTP aislado para el contrato Consultorio Web v1."""

import json
import uuid
from urllib import error, request

from django.conf import settings


class ConsultorioWebError(Exception):
    """Error administrativo seguro para mostrar en INTERA."""

    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def validar_configuracion():
    """Verifica la configuración sin revelar secretos."""

    if not settings.CONSULTORIOWEB_INTEGRATION_ENABLED:
        raise ConsultorioWebError(
            'integration_disabled',
            'La integración con Consultorio Web está deshabilitada.',
        )

    if not settings.CONSULTORIOWEB_API_BASE_URL:
        raise ConsultorioWebError(
            'configuration_error',
            'Falta la URL de Consultorio Web.',
        )

    if not settings.CONSULTORIOWEB_API_KEY:
        raise ConsultorioWebError(
            'configuration_error',
            'Falta la credencial de Consultorio Web.',
        )


def _request(method, path, payload=None, idempotency_key=None):
    validar_configuracion()

    headers = {
        'Authorization': f'ApiKey {settings.CONSULTORIOWEB_API_KEY}',
        'X-Contract-Version': '1',
        'X-Request-ID': str(uuid.uuid4()),
        'Accept': 'application/json',
    }

    data = None

    if payload is not None:
        headers['Content-Type'] = 'application/json'
        headers['Idempotency-Key'] = str(idempotency_key)
        data = json.dumps(payload).encode('utf-8')

    http_request = request.Request(
        f'{settings.CONSULTORIOWEB_API_BASE_URL}{path}',
        data=data,
        headers=headers,
        method=method,
    )

    try:
        response = request.urlopen(
            http_request,
            timeout=settings.CONSULTORIOWEB_API_TIMEOUT,
        )

        raw_body = response.read().decode('utf-8') or '{}'

        try:
            body = json.loads(raw_body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ConsultorioWebError(
                'contract_error',
                'Consultorio Web respondió en un formato no válido.',
            ) from exc

        return response.status, body

    except error.HTTPError as exc:
        try:
            body = json.loads(
                exc.read().decode('utf-8') or '{}'
            )
        except (ValueError, UnicodeDecodeError):
            body = {}

        return exc.code, body

    except ConsultorioWebError:
        raise

    except (
        error.URLError,
        TimeoutError,
        OSError,
        ValueError,
    ) as exc:
        raise ConsultorioWebError(
            'communication_error',
            'No fue posible comunicarse con Consultorio Web.',
        ) from exc


def _missing(label, value, missing):
    if not value:
        missing.append(label)


def payload_for(solicitud):
    """Construye solo los datos administrativos permitidos por el contrato v1."""

    canalizacion = solicitud.canalizacion
    participant = canalizacion.participante
    process = participant.proceso
    school = process.escuela
    missing = []

    _missing(
        'canalización',
        canalizacion.pk,
        missing,
    )

    _missing(
        'participante',
        participant.pk,
        missing,
    )

    _missing(
        'escuela',
        school.pk,
        missing,
    )

    _missing(
        'proceso de certificación',
        process.pk,
        missing,
    )

    _missing(
        'nombre completo',
        participant.nombre,
        missing,
    )

    _missing(
        'teléfono de contacto',
        participant.telefono,
        missing,
    )

    _missing(
        'motivo',
        canalizacion.motivo,
        missing,
    )

    _missing(
        'ciclo escolar',
        process.ciclo_escolar,
        missing,
    )

    _missing(
        'identificador externo',
        solicitud.external_request_id,
        missing,
    )

    _missing(
        'llave de idempotencia',
        solicitud.idempotency_key,
        missing,
    )

    if canalizacion.tipo not in {
        'ordinaria',
        'voluntaria',
        'emergencia',
    }:
        missing.append('tipo de solicitud válido')

    if canalizacion.prioridad not in {
        'baja',
        'media',
        'alta',
        'urgente',
    }:
        missing.append('prioridad válida')

    if missing:
        raise ConsultorioWebError(
            'validation_error',
            f"Completa: {', '.join(missing)}.",
        )

    priority = {
        'baja': 'normal',
        'media': 'normal',
        'alta': 'alta',
        'urgente': 'urgente',
    }[canalizacion.prioridad]

    data = {
        'external_request_id': str(
            solicitud.external_request_id
        ),
        'source': 'certificacion_intera',
        'request_type': canalizacion.tipo,
        'priority': priority,
        'participant': {
            'full_name': participant.nombre,
            'contact_phone': participant.telefono,
        },
        'school': {
            'external_id': str(school.pk),
            'name': school.nombre,
        },
        'certification_process': {
            'external_id': str(process.pk),
            'school_cycle': process.ciclo_escolar,
        },
        'reason': canalizacion.motivo,
        'consent': {
            'confirmed': True,
            'recorded_at': canalizacion.creada_en.isoformat(),
            'privacy_notice_version': 'intera-v1',
        },
        'referral_external_id': str(canalizacion.pk),
        'referral_date': canalizacion.fecha.isoformat(),
    }

    optional = {
        'birth_date': (
            participant.fecha_nacimiento.isoformat()
            if participant.fecha_nacimiento
            else None
        ),
        'sex': participant.sexo or None,
        'email': participant.correo or None,
        'student_number': participant.numero_alumno or None,
        'group': participant.grupo or None,
    }

    data['participant'].update(
        {
            key: value
            for key, value in optional.items()
            if value
        }
    )

    return data


def enviar_solicitud(solicitud):
    return _request(
        'POST',
        '/api/integraciones/intera/v1/solicitudes-atencion/',
        payload_for(solicitud),
        solicitud.idempotency_key,
    )


def consultar_estado(solicitud):
    return _request(
        'GET',
        (
            '/api/integraciones/intera/v1/'
            'solicitudes-atencion/'
            f'{solicitud.external_request_id}/'
        ),
    )