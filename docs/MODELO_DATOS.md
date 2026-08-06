# MODELO_DATOS.md

# Modelo de Datos

## Propósito

Definir el propietario de cada entidad principal de Plataforma INTRA.

Evitar duplicidad de modelos entre módulos.

---

# Portafolio

Propietario de:

- Documento
- Instrumento
- Pregunta
- Calculadora
- Plantilla de Entrevista
- Plantilla PDF
- Reporte
- Recurso Compartido

La estructura, secciones y preguntas reutilizables de la Entrevista 1:1 pertenecen a Portafolio.

Portafolio no administra aplicaciones individuales ni respuestas de participantes.

---

# Certificación INTERA

Propietario de:

- Escuela
- Expediente de Escuela
- Proceso
- Instrumento Configurado
- Aplicación
- Participante
- Respuesta
- Resultado
- Verificación de Acceso a Entrevista
- Entrevista 1:1
- Respuesta de Entrevista
- Historial de Entrevista
- Consejería
- Canalización
- Solicitud de Atención Clínica
- Bitácora

## Verificación de Acceso a Entrevista

Representa la solicitud realizada por Coordinación antes de abrir la Entrevista 1:1.

Deberá relacionarse con:

- Participante
- Proceso
- Coordinadora
- Fecha y hora
- Resultado de la verificación

INTERA comprobará:

- Coincidencia de los datos capturados.
- Pertenencia del participante al proceso.
- Finalización de los Instrumentos obligatorios.
- Ausencia de respuestas obligatorias pendientes.
- Permisos de la coordinadora.
- Estado actual de la entrevista.

La verificación no crea ni modifica participantes.

No deberá duplicar innecesariamente los datos personales del alumno.

---

## Entrevista 1:1

Representa la aplicación individual y asistida realizada por Coordinación junto con el alumno.

Cada Entrevista 1:1 pertenece a:

- Un participante
- Un proceso
- Una plantilla de entrevista de Portafolio
- Una coordinadora responsable

Solo podrá existir una Entrevista 1:1 por participante y proceso.

Estados:

- Bloqueada
- Disponible
- En curso
- Finalizada
- Reabierta

INTERA administra:

- Acceso
- Estado
- Borradores
- Respuestas
- Finalización
- Reapertura
- Historial

---

## Respuestas de Entrevista

Las respuestas pertenecen a:

- Entrevista 1:1
- Pregunta de Portafolio
- Participante
- Proceso

No deberán existir respuestas huérfanas.

Las respuestas no deberán convertirse automáticamente en diagnósticos.

Cualquier cálculo o alerta deberá utilizar reglas aprobadas y configuradas desde Portafolio.

---

# Consultorio Web

Propietario de:

- Recepción
- Solicitud de Atención Externa
- Paciente
- Agenda
- Cita
- Expediente Clínico
- Evolución
- Tratamiento

La Solicitud de Atención Externa representa en Consultorio Web la solicitud administrativa recibida desde INTERA.

No comparte modelos ni base de datos con la Solicitud de Atención Clínica de INTERA.

---

# Relaciones Generales

```text
Documento
    ↓
Instrumento
    ↓
Pregunta
    ↓
Instrumento Configurado
    ↓
Aplicación
    ↓
Respuesta
    ↓
Resultado
```

---

# Relaciones de la Entrevista 1:1

```text
Plantilla de Entrevista (Portafolio)
    ↓
Preguntas
    ↓
Proceso
    ↓
Participante
    ↓
Instrumentos obligatorios finalizados
    ↓
Verificación de Acceso
    ↓
Entrevista 1:1
    ↓
Respuestas de Entrevista
    ↓
Historial de Entrevista
```

---

# Relaciones de Atención Clínica

```text
Canalización (INTERA)
    ↓
Solicitud de Atención Clínica (INTERA)
    ↓
API
    ↓
Solicitud de Atención Externa (Consultorio Web)
    ↓
Paciente
    ↓
Cita
    ↓
Atención Clínica
```

La vinculación con Paciente y Cita se realiza únicamente dentro de Consultorio Web.

---

# Principios

- Cada entidad tiene un único propietario.
- No duplicar modelos entre módulos.
- Compartir información mediante API cuando corresponda.
- Mantener independencia entre dominios.
- Las plantillas y preguntas reutilizables pertenecen a Portafolio.
- Las aplicaciones y respuestas individuales pertenecen a INTERA.
- La información clínica pertenece a Consultorio Web.
- La verificación de acceso no sustituye ni duplica al participante.
- La Entrevista 1:1 es privada y exclusiva de Coordinación.

---

# Restricciones

- INTERA no administra Instrumentos.
- INTERA no crea Preguntas de Entrevista.
- Portafolio no administra Procesos.
- Portafolio no administra participantes ni respuestas individuales.
- Consultorio Web no administra Certificaciones.
- Consultorio Web no administra Entrevistas 1:1.
- INTERA no administra Pacientes, Citas ni Expedientes Clínicos.
- Ningún módulo deberá acceder directamente a la base de datos de otro.
- El Excel original no deberá almacenarse en el repositorio.
- No utilizar datos reales del Excel como datos de prueba.
- No copiar cálculos o reglas del Excel sin validación previa.

---

# Regla de Oro

Antes de crear un nuevo modelo responder:

**¿Esta entidad ya pertenece a otro módulo?**

Si la respuesta es sí, reutilizarla o consumirla mediante integración.

La plantilla pertenece a Portafolio.

La aplicación de la Entrevista 1:1 pertenece a INTERA.

La atención clínica pertenece a Consultorio Web.