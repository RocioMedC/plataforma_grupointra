# INTEGRACION_CONSULTORIOWEB.md

# Integración con Consultorio Web

## Propósito

Definir la comunicación entre Plataforma INTRA y Consultorio Web.

La integración permitirá que Certificación INTERA solicite atención clínica para un participante sin administrar información clínica.

Consultorio Web continuará siendo el propietario de todos los procesos clínicos.

---

# Responsabilidades

## Plataforma INTRA

Responsable de:

- Generar Solicitudes de Atención Clínica.
- Enviar solicitudes a Consultorio Web.
- Consultar el estado de las solicitudes.
- Mostrar el seguimiento dentro de INTERA.
- Conservar la trazabilidad administrativa del envío.

No administra:

- Pacientes.
- Agenda.
- Expedientes Clínicos.
- Evoluciones.
- Tratamientos.
- Notas Clínicas.

---

## Consultorio Web

Responsable de:

- Recibir Solicitudes de Atención Clínica.
- Mostrar las solicitudes en una bandeja para Recepción.
- Revisar la información recibida.
- Buscar pacientes existentes.
- Vincular la solicitud con un paciente existente.
- Crear un paciente mediante el flujo normal cuando sea necesario.
- Administrar la agenda.
- Administrar los expedientes clínicos.
- Actualizar el estado administrativo de la solicitud.

Consultorio Web decidirá si un participante corresponde a un paciente existente o requiere crear uno nuevo.

Consultorio Web no deberá crear pacientes automáticamente al recibir una solicitud.

No deberá crear citas automáticamente desde la API.

Recepción deberá revisar primero la solicitud, vincular o registrar al paciente según corresponda y posteriormente utilizar el flujo normal de agenda de Consultorio Web.

---

# Comunicación

Toda comunicación entre ambos sistemas deberá realizarse mediante API.

No deberá existir acceso directo entre bases de datos.

No deberán compartirse modelos, migraciones ni archivos Python entre los repositorios.

La integración deberá poder deshabilitarse sin afectar el funcionamiento de ninguno de los sistemas.

---

# Información Compartida

Plataforma INTRA podrá enviar únicamente la información necesaria para solicitar atención.

Ejemplo:

- Participante.
- Escuela.
- Proceso.
- Tipo de Solicitud.
- Prioridad.
- Motivo.
- Datos de contacto.

Consultorio Web únicamente devolverá información relacionada con el estado administrativo de la solicitud.

Nunca compartirá información clínica.

---

# Tipos de Solicitud

- Ordinaria.
- Emergencia.
- Voluntaria.

Cada Solicitud de Atención Clínica siempre deberá originarse desde una Canalización registrada en INTERA.

---

# Estados de la Solicitud

Estados sugeridos:

- Pendiente de envío.
- Enviada.
- Recibida.
- En revisión.
- Información incompleta.
- Paciente vinculado.
- Paciente registrado.
- Contacto realizado.
- Cita programada.
- En atención.
- Finalizada.
- Rechazada.
- Cancelada.
- Error de comunicación.

Los estados podrán ampliarse posteriormente sin modificar la arquitectura.

---

# Principios de Arquitectura

- Cada sistema administra únicamente su propio dominio.
- La información clínica permanece en Consultorio Web.
- INTERA administra únicamente el seguimiento de la certificación.
- Toda comunicación se realiza mediante API.
- Mantener independencia entre ambos sistemas.

---

# Reglas Obligatorias

- Toda Solicitud pertenece a un participante.
- Toda Solicitud pertenece a un proceso.
- Toda Solicitud deberá registrarse en Bitácora.
- No crear pacientes automáticamente.
- No crear citas automáticamente desde la API.
- Recepción será responsable de crear o vincular pacientes.
- Recepción utilizará el flujo normal de agenda.
- Mantener trazabilidad durante todo el proceso.

---

# Restricciones de Arquitectura

Plataforma INTRA NO deberá:

- Crear pacientes.
- Modificar expedientes clínicos.
- Agendar citas.
- Registrar notas clínicas.
- Consultar expedientes clínicos.
- Acceder directamente a la base de datos de Consultorio Web.

Consultorio Web NO deberá:

- Administrar procesos de certificación.
- Administrar Instrumentos.
- Administrar Participantes de INTERA.

Cada sistema mantiene su propio dominio de negocio.

---

# Lineamientos de Desarrollo

Antes de modificar la integración:

1. Leer PLATAFORMA_INTRA.md.
2. Leer INTERA.md.
3. Leer este documento.
4. Mantener compatibilidad con ambos sistemas.
5. Implementar únicamente comunicación mediante API.
6. No modificar funcionalidades existentes de Consultorio Web.
7. Mantener la integración desacoplada.

---

# Estado Actual

| Componente | Estado |
|------------|--------|
| Arquitectura | Definida |
| Análisis de Consultorio Web | Completado |
| API | Pendiente |
| Comunicación | Pendiente |
| Sincronización de estados | Pendiente |

---

# Regla de Oro

Plataforma INTRA solicita atención.

Consultorio Web recibe la solicitud, Recepción conserva el control del proceso y administra pacientes y agenda mediante sus flujos normales.

Ambos sistemas deberán permanecer independientes y comunicarse únicamente mediante una API desacoplada.