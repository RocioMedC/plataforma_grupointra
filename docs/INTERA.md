# Certificación INTERA

## Propósito

Certificación INTERA administra el proceso de certificación de instituciones educativas, desde la escuela y el proceso hasta el seguimiento de participantes. Los recursos reutilizables pertenecen a Portafolio; la información clínica pertenece a Consultorio Web.

## Flujo

Escuela → Proceso de certificación → Configuración de instrumentos → Participantes → Aplicaciones → Resultados → Entrevista 1:1 → Consejerías → Canalizaciones → Solicitud de Atención Clínica.

Cada participante pertenece a un único proceso. Las respuestas, aplicaciones, resultados, entrevistas, consejerías y canalizaciones se relacionan con ese proceso.

## Responsabilidades

INTERA administra escuelas, expedientes, procesos, participantes, aplicaciones, respuestas, resultados, entrevista 1:1, consejerías, canalizaciones, solicitudes de atención y bitácora.

Portafolio provee instrumentos, preguntas, calculadoras, plantillas de entrevista, plantillas PDF, reportes y recursos compartidos. INTERA no crea ni duplica esos recursos.

Consultorio Web administra pacientes, agenda, expedientes y notas clínicas. INTERA sólo intercambia Solicitudes de Atención Clínica mediante API, sin transferir información clínica innecesaria.

## Acceso y navegación

- El grupo técnico de operación es `Certificación`; la etiqueta visible es Coordinación INTERA.
- Los usuarios exclusivos de Certificación se redirigen al Panel INTERA al iniciar sesión.
- Dirección y Sistemas conservan el Portal general y sus permisos actuales.
- Todas las rutas de INTERA validan autorización en el servidor.
- El usuario operativo inicial se crea con un comando administrativo interactivo seguro; las contraseñas no se almacenan en código, migraciones ni documentos.
- El menú lateral contiene Panel, Escuelas, Procesos, Participantes, Entrevistas, Seguimiento y Configuración.
- Cerrar sesión está en la parte inferior izquierda, usa POST con CSRF y el menú se puede abrir y cerrar en móvil.

## Reglas principales

- Los instrumentos configurados provienen de Portafolio y usan enlaces públicos con UUID.
- No deben existir respuestas duplicadas ni huérfanas.
- Los resultados se calculan con servicios de Portafolio.
- La Entrevista 1:1 es privada, asistida y exclusiva de Coordinación INTERA; conserva borradores e historial.
- La entrevista requiere instrumentos obligatorios finalizados y validación de identidad del participante.
- Las consejerías conservan historial y se limitan a tres por participante.
- Las canalizaciones y solicitudes de atención se registran en bitácora.

## Validación mínima

Después de cambios relevantes ejecutar `manage.py check`, pruebas automatizadas aplicables, comprobación de enlaces públicos, permisos, bitácora, resultados e integración con Portafolio y Consultorio Web.

## Navegación operativa

El Panel reúne indicadores, acciones rápidas, trabajo pendiente, escuelas recientes y procesos activos. Escuelas y Procesos son catálogos independientes con búsqueda, filtros GET y paginación. Las fichas conservan la URL de retorno interna para volver al listado filtrado.

El progreso de batería es participantes con todas sus aplicaciones respondidas entre participantes del proceso; sin participantes es 0 %. El proceso usa pestañas reflejadas en `?tab=` y los procesos cerrados se muestran en modo consulta.

Las escuelas similares se revisan antes de registrarse. Nombre, correo y teléfono se comparan normalizados; la confirmación usa un estado temporal de sesión, POST con CSRF, expira a los 20 minutos y se consume al guardar. La Ficha de escuela usa pestañas, muestra el director almacenado, separa capacidad de participantes y conserva el retorno interno al catálogo.

## Aplicación pública de batería

Cada proceso puede tener un único enlace público general, idempotente y separado de las vistas individuales por instrumento. Coordinación puede generarlo, mostrarlo, copiarlo, abrirlo, activarlo o desactivarlo; al activarlo el proceso pasa a Aplicación de instrumentos. El enlace inicia con datos generales, vincula o crea un participante por matrícula dentro del proceso sin crear cuentas, y reanuda aplicaciones pendientes en el orden configurado.

La batería pública presenta instrucciones antes de cada instrumento, no incluye Entrevista 1:1 ni instrumentos bloqueados, no muestra resultados y solicita una única aceptación del aviso de privacidad INTERA v1 antes del envío definitivo. La aceptación y su fecha se almacenan en el participante. Los procesos cerrados conservan consulta interna, pero no admiten operaciones públicas nuevas.
