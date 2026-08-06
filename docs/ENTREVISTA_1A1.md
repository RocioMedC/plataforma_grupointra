# Entrevista 1:1 de Certificación INTERA

## Propósito
Definir la entrevista asistida que Coordinación realiza junto con el alumno dentro de un Proceso de Certificación.

Es privada, exclusiva de Coordinación y se basa en la hoja `ENTREVISTA` del archivo institucional revisado.

El Excel original contiene datos sensibles y no deberá almacenarse en el repositorio ni utilizarse como fuente de pruebas.

# Responsabilidades

## Portafolio
Propietario del Documento e Instrumento origen, Plantilla, secciones, Preguntas, opciones, condicionales, orden y versión.

## Certificación INTERA
Propietario de la verificación de requisitos e identidad, aplicación individual, respuestas, borradores, estados, historial y Bitácora.

# Acceso

Solo Coordinación podrá ver, solicitar acceso, contestar, guardar, finalizar, consultar y reabrir la entrevista.

El alumno no tendrá acceso directo ni mediante enlaces públicos. Los permisos también deberán validarse al acceder por URL.

# Requisitos Previos

INTERA verificará automáticamente que:
- El participante pertenece al proceso.
- Tiene aplicación para cada Instrumento obligatorio.
- Todas las aplicaciones están finalizadas.
- No existen respuestas obligatorias pendientes.
- La usuaria pertenece a Coordinación.
- La entrevista no fue finalizada previamente.

No se utilizará una confirmación manual para indicar que el alumno contestó todo.

# Solicitud de Acceso

Coordinación deberá capturar nuevamente:
- Número de alumno.
- Nombre completo.
- Fecha de nacimiento.

INTERA comparará los datos con el participante seleccionado.

Reglas:
- No crear ni modificar participantes.
- No guardar una segunda ficha del alumno.
- Registrar usuaria, fecha, participante y resultado.
- No revelar qué dato fue incorrecto.
- Registrar cada intento en Bitácora.

```text
Instrumentos completos
    ↓
Solicitud de acceso
    ↓
Verificación de identidad
    ↓
Entrevista disponible
    ↓
Borrador / Finalización
```

# Datos Precargados

Al abrir la entrevista se mostrarán:
- Nombre y número de alumno.
- Edad, sexo y fecha de nacimiento.
- Escuela, proceso, ciclo y grupo.
- Fecha de elaboración.
- Coordinadora responsable.

Estos datos no se capturarán nuevamente dentro de la entrevista.

# Estados

- `bloqueada`: faltan requisitos.
- `disponible`: puede solicitarse el acceso.
- `en_curso`: admite respuestas y borradores.
- `finalizada`: cerrada y de solo lectura.
- `reabierta`: habilitada con autorización y justificación.

Solo podrá existir una entrevista por participante y proceso.

# Preguntas

La entrevista contiene cuatro secciones y 24 campos.

## Motivación para concluir el programa

| Clave | Pregunta | Tipo |
|---|---|---|
| MOT-01 | ¿Por qué eligió este programa para estudiar? | Texto largo, obligatorio |
| MOT-02 | ¿Tienes algún plan para concluir tu carrera? | Sí/No, obligatorio |
| MOT-03 | ¿Cuál? | Texto, si MOT-02 = Sí |
| MOT-04 | Del 1 al 10, ¿qué tan motivado se encuentra para concluir el programa? | Entero 1–10, obligatorio |

## Riesgo de deserción

| Clave | Pregunta | Tipo |
|---|---|---|
| DES-01 | ¿Usted o su familia padece alguna enfermedad crónica? | Sí/No, obligatorio |
| DES-02 | ¿Qué enfermedad? | Texto, si DES-01 = Sí |
| DES-03 | Parentesco | Texto, si DES-01 = Sí |
| DES-04 | ¿Usted o su familia padece alguna enfermedad mental? | Sí/No, obligatorio |
| DES-05 | ¿Qué enfermedad? | Texto, si DES-04 = Sí |
| DES-06 | Parentesco | Texto, si DES-04 = Sí |
| DES-07 | Si ocurriera algo que te hiciera abandonar la escuela, ¿qué sería? | Texto largo, obligatorio |
| DES-08 | ¿Quién soporta tus gastos personales y educativos? | Texto largo, obligatorio |
| DES-09 | ¿Cómo podrías solventar tus gastos de otra manera? | Texto largo, obligatorio |

El Excel no define una regla completa para calcular un nivel general de deserción. INTERA no deberá inventarla.

## Resiliencia y superación

| Clave | Pregunta | Tipo |
|---|---|---|
| RES-01 | ¿Has sido víctima de algún tipo de acoso escolar? | Sí/No, obligatorio |
| RES-02 | ¿Conoces qué es el acoso escolar o bullying y sus consecuencias? | Sí/No, obligatorio |
| RES-03 | Observaciones | Texto largo, opcional |

La clasificación del Excel no deberá activarse hasta ser validada por la responsable del programa.

## MODORIS

El archivo usa los nombres `MODORIS` y `ASQ MODORIS`. El nombre oficial y sus reglas deberán confirmarse.

| Clave | Pregunta | Tipo |
|---|---|---|
| MOD-01 | En las últimas semanas, ¿ha deseado estar muerto? | Sí/No, obligatorio |
| MOD-02 | En las últimas semanas, ¿ha sentido que usted o su familia estarían mejor si estuviera muerto? | Sí/No, obligatorio |
| MOD-03 | En la última semana, ¿ha pensado en suicidarse? | Sí/No, obligatorio |
| MOD-04 | ¿Alguna vez ha intentado suicidarse? | Sí/No, obligatorio |
| MOD-05 | ¿Cómo lo hizo? | Texto largo, si MOD-04 = Sí |
| MOD-06 | ¿Cuándo lo hizo? | Texto, si MOD-04 = Sí |
| MOD-07 | ¿Está pensando en suicidarse en este momento? | Sí/No, obligatorio |
| MOD-08 | Describa estos pensamientos: planes, intención o preparativos | Texto largo, si MOD-07 = Sí |

# Cálculos y Alertas

Las fórmulas del Excel no se consideran reglas aprobadas.

INTERA deberá:
- Guardar respuestas estructuradas.
- No copiar fórmulas sin validación.
- No generar diagnósticos ni impresiones diagnósticas.
- Usar posteriormente Calculadoras de Portafolio aprobadas.

Antes de activar alertas deberá definirse:
- Qué respuestas generan alerta.
- Nivel y responsable de atención.
- Acción obligatoria de Coordinación.
- Relación con Canalización de Emergencia.
- Si puede finalizarse con una alerta pendiente.

# Captura y Finalización

- Permitir guardar borrador y continuar.
- Validar preguntas obligatorias visibles.
- Almacenar Sí/No como valores controlados.
- Aceptar solo enteros del 1 al 10 en MOT-04.
- Limpiar respuestas condicionales que dejen de aplicar.
- Conservar pregunta y versión de plantilla.
- No alterar entrevistas finalizadas al modificar Portafolio.

Al finalizar:
- Registrar fecha, hora y coordinadora.
- Bloquear edición.
- Conservar historial y versión.
- Registrar el evento en Bitácora.

La finalización no crea automáticamente Consejerías, Canalizaciones, Solicitudes de Atención, pacientes, citas ni diagnósticos.

# Reapertura

Requiere usuaria autorizada, justificación, fecha, historial y Bitácora.

# Bitácora y Privacidad

Registrar:
- Verificación de requisitos.
- Solicitud e intento de acceso.
- Inicio, borrador, finalización y reapertura.
- Accesos rechazados.

No registrar:
- Respuestas completas.
- Contenido sensible de MODORIS.
- Datos capturados para verificar identidad.
- Diagnósticos.

La entrevista no se compartirá con Consultorio Web mediante la API de Solicitudes de Atención.

# Experiencia de Usuario

En el expediente del participante mostrar:
- Progreso e Instrumentos pendientes.
- Estado de la Entrevista 1:1.
- Acción disponible según el estado.

La entrevista se organizará por secciones con indicador de progreso.

# Validaciones Obligatorias

- Acceso exclusivo de Coordinación.
- Bloqueo por URL para usuarios no autorizados.
- Instrumentos completos antes del acceso.
- Verificación correcta e incorrecta de identidad.
- Una entrevista por participante y proceso.
- Las 24 preguntas, tipos y condicionales.
- Borradores, finalización y reapertura.
- Historial y Bitácora.
- Ausencia de diagnósticos y datos sensibles en logs.

# Pendientes de Validación

1. Nombre oficial de MODORIS.
2. Reglas aprobadas de riesgo y alertas.
3. Protocolo ante atención inmediata.
4. Relación con Consejerías y Canalizaciones.
5. Quién autoriza la reapertura.

# Estado Actual

| Componente | Estado |
|---|---|
| Estructura y preguntas | Definidas |
| Arquitectura y acceso | Definidos |
| Reglas de cálculo | Pendientes de validación |
| Plantilla en Portafolio | Pendiente |
| Aplicación en INTERA | Pendiente |

# Regla de Oro

La entrevista solo se habilita cuando el alumno completó todos los Instrumentos obligatorios y Coordinación verificó nuevamente su identidad.

Portafolio administra la estructura e INTERA administra el acceso, aplicación y respuestas.
