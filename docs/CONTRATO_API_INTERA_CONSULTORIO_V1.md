# Contrato API INTERA - ConsultorioWeb v1

## 1. Arquitectura del contrato

- Comunicacion exclusiva mediante API HTTPS.
- INTERA crea y conserva su `SolicitudAtencionClinica`.
- ConsultorioWeb recibe y administra su solicitud operativa.
- ConsultorioWeb conserva el control de recepcion, paciente, agenda y expediente.
- INTERA consulta unicamente el estado administrativo.
- No hay acceso directo a bases de datos, modelos compartidos ni sincronizacion clinica.

## 2. Endpoints minimos

| Metodo | Endpoint | Proposito |
|---|---|---|
| `POST` | `/api/integraciones/intera/v1/solicitudes-atencion/` | Registrar una solicitud externa de atencion. |
| `GET` | `/api/integraciones/intera/v1/solicitudes-atencion/{external_request_id}/` | Consultar el estado administrativo actualizado. |

No se recomienda `PATCH` desde INTERA: la recepcion de ConsultorioWeb controla los cambios de estado. Tampoco se requieren endpoints de pacientes o agenda.

## 3. Payload de envio

### Obligatorio

```json
{
  "external_request_id": "UUID inmutable generado por INTERA",
  "source": "certificacion_intera",
  "request_type": "ordinaria | emergencia | voluntaria",
  "priority": "normal | alta | urgente",
  "participant": {
    "full_name": "Nombre completo",
    "contact_phone": "Telefono de contacto"
  },
  "school": {
    "external_id": "Identificador de escuela en INTERA",
    "name": "Nombre de la escuela"
  },
  "certification_process": {
    "external_id": "Identificador del proceso",
    "school_cycle": "2026-2027"
  },
  "reason": "Motivo administrativo de la solicitud",
  "consent": {
    "confirmed": true,
    "recorded_at": "2026-08-03T12:00:00-06:00",
    "privacy_notice_version": "v1"
  }
}
```

### Opcional

- Fecha de nacimiento.
- Sexo.
- Correo.
- Numero de alumno.
- Grupo.
- Persona responsable y telefono alterno.
- Observacion administrativa breve.
- Fecha de canalizacion.
- Referencia externa de la canalizacion.

### No permitida

- Respuestas de instrumentos.
- Puntajes, interpretaciones o resultados psicologicos.
- Entrevistas, consejerias o notas.
- Diagnosticos.
- Expediente clinico.
- Antecedentes medicos o psiquiatricos.
- Informacion de tratamientos o citas previas.
- Credenciales, IDs internos de usuarios o datos de otros participantes.

## 4. Respuestas de ConsultorioWeb

Respuesta a `POST` exitoso:

```json
{
  "internal_request_id": "CW-12345",
  "external_request_id": "UUID recibido",
  "status": "recibida",
  "updated_at": "2026-08-03T12:05:00-06:00",
  "message": "Solicitud recibida y disponible para Recepcion."
}
```

Respuesta a `GET`:

```json
{
  "external_request_id": "UUID recibido",
  "status": "contacto_realizado",
  "updated_at": "2026-08-04T09:30:00-06:00",
  "message": "Recepcion realizo el primer contacto."
}
```

Nunca incluir paciente interno, terapeuta, expediente, diagnostico, cita especifica ni informacion clinica.

## 5. Estados definitivos

Los estados `pendiente_envio`, `enviada` y `error_comunicacion` son internos de INTERA. ConsultorioWeb administra los siguientes:

| Estado | Lo cambia | Siguiente estado valido |
|---|---|---|
| `recibida` | API de ConsultorioWeb | `en_revision`, `rechazada`, `cancelada` |
| `en_revision` | Recepcion | `informacion_incompleta`, `paciente_vinculado`, `paciente_registrado`, `rechazada`, `cancelada` |
| `informacion_incompleta` | Recepcion | `en_revision`, `rechazada`, `cancelada` |
| `paciente_vinculado` | Recepcion | `contacto_realizado`, `cita_programada`, `cancelada` |
| `paciente_registrado` | Recepcion, mediante flujo normal | `contacto_realizado`, `cita_programada`, `cancelada` |
| `contacto_realizado` | Recepcion | `cita_programada`, `cancelada` |
| `cita_programada` | Recepcion, despues de usar agenda normal | `en_atencion`, `cancelada` |
| `en_atencion` | Personal autorizado de ConsultorioWeb | `finalizada`, `cancelada` |
| `finalizada` | Personal autorizado | Terminal |
| `rechazada` | Recepcion | Terminal |
| `cancelada` | Recepcion | Terminal |

`informacion_incompleta` no obliga a que INTERA actualice por API en v1. Recepcion puede completar o aclarar los datos por sus canales normales. Si se requiere corregir el origen, INTERA debe cancelar la solicitud previa y crear otra con un nuevo identificador externo.

## 6. Errores estandar

| Codigo | Uso |
|---|---|
| `400` | JSON invalido, encabezado requerido ausente o formato incorrecto. |
| `401` | API Key ausente, vencida o invalida. |
| `403` | Credencial valida sin permiso para la integracion INTERA. |
| `404` | `external_request_id` inexistente al consultar estado. |
| `409` | Misma llave de idempotencia con payload distinto, o conflicto de identificador externo. |
| `422` | Payload valido como JSON, pero falla una regla de negocio: consentimiento ausente, tipo no permitido, telefono faltante, etc. |
| `429` | Limite de solicitudes excedido. |
| `500` | Error interno no atribuible a INTERA. |

Las respuestas de error deben incluir: `code`, `message`, `request_id` y, solo cuando aplique, `field_errors`.

## 7. Autenticacion

Mecanismo recomendado:

- API Key de servicio exclusiva para INTERA, distinta de una llave global.
- Autenticacion mediante `X-API-Key`.
- HTTPS obligatorio.
- La llave se guarda unicamente en variables de entorno.
- Rotacion periodica y posibilidad de revocacion.

Encabezados:

```text
Authorization: ApiKey <credencial-de-servicio>
X-API-Key: <credencial-de-servicio>
X-Contract-Version: 1
X-Request-ID: UUID por intento HTTP
Idempotency-Key: UUID por solicitud logica
Content-Type: application/json
Accept: application/json
```

Debe elegirse solo uno entre `Authorization` y `X-API-Key` al implementar; se recomienda `Authorization: ApiKey` y reservar `X-API-Key` para compatibilidad si fuera necesario.

## 8. Idempotencia y reintentos

- `external_request_id` identifica permanentemente la solicitud de INTERA.
- `Idempotency-Key` identifica el intento logico de creacion.
- ConsultorioWeb debe almacenar ambos y una huella del payload.
- Si llega el mismo identificador con el mismo payload, devuelve la solicitud existente sin crear duplicado.
- Si llega con el mismo identificador y contenido diferente, responde `409`.
- Ante timeout, INTERA reintenta el mismo `POST` con los mismos identificadores.
- Reintentos sugeridos: 1 min, 5 min, 15 min, 1 h; despues, marcar `error_comunicacion` y permitir reintento manual.
- Nunca crear una nueva solicitud por un timeout sin antes consultar por `external_request_id`.

## 9. Versionado

- URL versionada: `/v1/`.
- El encabezado `X-Contract-Version: 1` funciona como validacion adicional.
- Agregar campos opcionales no rompe `v1`.
- Cambiar semantica, eliminar campos o alterar estados requiere `/v2/`.
- ConsultorioWeb debe mantener `v1` durante un periodo de transicion acordado.

## 10. Flujo completo

```text
INTERA
  ↓
Crea Solicitud de Atencion Clinica y Bitacora
  ↓
POST /v1/solicitudes-atencion/
  ↓
ConsultorioWeb valida autenticacion, consentimiento e idempotencia
  ↓
Solicitud externa queda en bandeja de Recepcion
  ↓
Recepcion revisa y vincula o registra paciente
  ↓
Recepcion usa el flujo normal de agenda
  ↓
ConsultorioWeb actualiza estado administrativo
  ↓
INTERA consulta GET por external_request_id
  ↓
INTERA muestra estado y registra cambio en Bitacora
```

## 11. Riesgos

- Consentimiento insuficiente o no verificable.
- Duplicados por reintentos sin idempotencia.
- Exposicion accidental de resultados o notas clinicas.
- Dependencia de una llave compartida sin rotacion.
- Estados ambiguos si se intenta inferir la atencion desde pacientes o citas.
- Automatizar creacion de pacientes o citas, contradiciendo el flujo actual de recepcion.

## 12. Recomendaciones antes de programar

- Validar con el cliente el texto y evidencia del consentimiento para compartir datos de contacto.
- Definir quien puede cancelar una solicitud y en que momento.
- Confirmar si `urgente` requiere canal alterno de atencion ademas de la API.
- Acordar mensajes administrativos permitidos y prohibidos.
- Definir retencion de datos y auditoria de accesos.
- Confirmar el periodo de compatibilidad de `v1`.
- Implementar primero el receptor y bandeja de ConsultorioWeb; despues el emisor de INTERA.
