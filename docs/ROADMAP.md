# Roadmap — Plataforma INTRA

## Estado actual

La plataforma se encuentra en MVP. Los módulos activos son Portafolio y Certificación INTERA; Consultorio Web se integra como sistema externo.

### Portafolio

MVP funcional para instrumentos, preguntas, calculadoras, documentos, plantillas PDF, reportes y recursos reutilizables.

### Certificación INTERA

MVP funcional para escuelas, expedientes, procesos, configuración de instrumentos, participantes, aplicaciones, resultados, entrevista 1:1, seguimiento, consejerías, canalizaciones, bitácora e integración con Consultorio Web.

## Acceso a Certificación INTERA

- `Certificación` es el grupo técnico operativo.
- `Coordinación INTERA` es su etiqueta funcional visible.
- Los usuarios exclusivos de Certificación inician directamente en el Panel INTERA.
- Dirección y Sistemas mantienen el Portal general y sus accesos autorizados.
- Las rutas de INTERA se protegen en el servidor; ocultar enlaces no sustituye la autorización.
- El primer usuario operativo se prepara mediante un comando interactivo seguro. Las contraseñas nunca se almacenan en código, migraciones ni documentación.
- El menú lateral incluye Panel, Escuelas, Procesos, Participantes, Entrevistas, Seguimiento y Configuración. El cierre de sesión permanece abajo a la izquierda y utiliza POST con CSRF; el menú dispone de comportamiento móvil.

## Próximas prioridades

1. Consolidar la estabilidad del MVP y la experiencia de los flujos existentes.
2. Reportes institucionales y generación de PDF.
3. Dashboard ejecutivo y mejoras de experiencia de usuario.

La operación de INTERA se organiza alrededor de Panel → Escuela → Proceso. Los catálogos usan filtros en la URL y las fichas de proceso usan pestañas con rutas reales, preservando el patrón POST → redirect → GET.

La Ficha de escuela conserva el retorno interno entre sus pestañas. El registro revisa coincidencias y requiere una confirmación temporal de un solo uso antes de crear una escuela con datos similares.

La aplicación pública general de la batería está integrada: usa un enlace único por proceso, registro o vinculación de participante sin cuentas, reanudación, orden de instrumentos, instrucciones y aceptación de privacidad. Entrevista 1:1 permanece como flujo privado de Coordinación.

## Futuro

CRM, Finanzas, Academia, NOM-035, notificaciones, agenda institucional, firma electrónica, versionado documental y BI se evaluarán en versiones posteriores.

## Regla de desarrollo

Toda modificación debe respetar la arquitectura de Plataforma INTRA, Portafolio, INTERA, el modelo de datos y el contrato con Consultorio Web. No se duplican recursos compartidos ni lógica clínica.
