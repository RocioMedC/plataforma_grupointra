# PORTAFOLIO.md

# Portafolio INTRA

## Propósito

Portafolio es la biblioteca institucional de recursos reutilizables de Plataforma INTRA.

Su responsabilidad es administrar los recursos compartidos utilizados por los diferentes módulos de la plataforma.

Portafolio no implementa procesos de negocio.

---

# Componentes

## Documentos

Repositorio principal de archivos institucionales.

Cada documento almacena como mínimo:

- Nombre
- Archivo
- Categoría
- Tipo
- Estado
- Versión
- Usuario
- Fecha de carga
- Observaciones

Todo recurso reutilizable deberá registrarse inicialmente como un Documento.

---

## Instrumentos

Los Instrumentos se crean a partir de un Documento registrado en Portafolio.

Cada Instrumento mantiene una referencia permanente al Documento origen.

Portafolio es el único propietario de los Instrumentos.

---

## Preguntas

Las Preguntas pertenecen exclusivamente a un Instrumento.

Pueden crearse manualmente o mediante procesos de importación.

Los módulos consumidores nunca deberán crear Preguntas.

---

## Plantillas de Entrevista

Las Plantillas de Entrevista son configuraciones reutilizables para aplicaciones asistidas.

Se construyen a partir de un Instrumento de Portafolio y utilizan sus Preguntas.

Cada plantilla podrá definir:

- Secciones
- Orden de preguntas
- Tipo de respuesta
- Campos obligatorios
- Preguntas condicionales
- Reglas de visibilidad
- Estado
- Versión

Portafolio administra únicamente la estructura reutilizable.

El módulo consumidor administra:

- Acceso
- Participante
- Aplicación individual
- Respuestas
- Borradores
- Finalización
- Historial

La Plantilla de Entrevista 1:1 será consumida por Certificación INTERA.

---

## Calculadoras

Las Calculadoras contienen la lógica de evaluación e interpretación de los Instrumentos.

Ejemplos actuales:

- SCID-II

Preparadas para incorporar posteriormente:

- SCL-90
- DASS-21
- ISRA
- Raven
- Allport
- TCI
- TDS

Los módulos consumidores únicamente envían respuestas y reciben resultados.

Nunca deberán implementar lógica propia de cálculo.

Las reglas de alerta relacionadas con una Plantilla de Entrevista deberán estar previamente aprobadas antes de configurarse.

No deberán generar diagnósticos automáticamente.

---

## Plantillas PDF

Repositorio institucional de plantillas.

Ejemplos:

- Certificados
- Reportes
- Constancias
- Oficios

Las plantillas serán reutilizadas por cualquier módulo.

---

## Reportes

Configuraciones reutilizables para generación de reportes.

El contenido será proporcionado por el módulo consumidor.

Portafolio administra únicamente las plantillas y recursos necesarios para su generación.

---

## Recursos Compartidos

Repositorio para recursos reutilizables.

Ejemplos:

- Logotipos
- Iconografía
- Imágenes
- Multimedia
- Plantillas de correo
- Recursos institucionales

---

## Servicios Compartidos

Portafolio podrá proporcionar servicios reutilizables para toda la plataforma.

Ejemplos:

- Cálculo de instrumentos.
- Generación de PDF.
- Generación de reportes.
- Importación de recursos.
- Conversión de formatos.

---

# Arquitectura General

```text
Documento
    │
    ▼
Instrumento
    │
    ▼
Preguntas
    │
    ├── Calculadora
    │
    └── Plantilla de Entrevista
            │
            ▼
      Módulos consumidores
```

---

# Módulos Consumidores

Actualmente:

- Certificación INTERA

Preparado para:

- CRM
- Finanzas
- Academia
- NOM-035
- Recursos Humanos
- Otros módulos futuros

---

# Integración con Certificación INTERA

Portafolio proporcionará a INTERA:

- Instrumentos
- Preguntas
- Calculadoras
- Plantillas de Entrevista
- Plantillas PDF
- Reportes

Para la Entrevista 1:1, Portafolio será propietario de:

- Documento origen
- Instrumento
- Preguntas
- Secciones
- Orden
- Opciones de respuesta
- Condicionales
- Versión de la plantilla

INTERA será propietario de:

- Verificación de acceso
- Participante
- Aplicación de la entrevista
- Respuestas
- Estado
- Borradores
- Finalización
- Reapertura
- Historial
- Bitácora

Portafolio no conocerá qué participante respondió una entrevista.

---

# Principios de Arquitectura

- Portafolio es el propietario de todos los recursos compartidos.
- Un recurso reutilizable deberá existir una sola vez.
- Los módulos consumidores nunca almacenarán copias de los recursos.
- Toda lógica reutilizable deberá implementarse en Portafolio.
- Portafolio no conocerá procesos de negocio.
- Las preguntas reutilizables pertenecen a Portafolio.
- Las aplicaciones y respuestas individuales pertenecen al módulo consumidor.
- Una Plantilla de Entrevista no representa una entrevista contestada.

---

# Reglas Obligatorias

- Todo Instrumento deberá originarse desde un Documento.
- Toda Pregunta deberá pertenecer a un Instrumento.
- Toda Calculadora deberá pertenecer a Portafolio.
- Toda Plantilla de Entrevista deberá relacionarse con un Instrumento.
- Los módulos consumidores no podrán modificar Instrumentos ni Preguntas.
- Los módulos consumidores no podrán modificar directamente una Plantilla de Entrevista.
- Los recursos compartidos deberán ser reutilizables.
- Mantener trazabilidad entre Documento e Instrumento.
- Mantener versionado de las Plantillas de Entrevista.
- No modificar una versión utilizada por aplicaciones finalizadas.
- No copiar fórmulas o reglas del Excel sin validación previa.
- No almacenar datos reales del Excel en Portafolio.

---

# Restricciones de Arquitectura

Portafolio NO administra:

- Escuelas
- Procesos
- Participantes
- Aplicaciones individuales
- Respuestas de participantes
- Resultados individuales
- Verificaciones de acceso
- Entrevistas contestadas
- Borradores de entrevista
- Historial de entrevista
- Consejerías
- Canalizaciones
- Solicitudes de Atención Clínica
- Pacientes
- Agenda
- Clientes
- Ventas
- Facturación
- Usuarios
- Roles

Toda lógica de negocio pertenece al módulo consumidor.

---

# Lineamientos de Desarrollo

Antes de modificar Portafolio:

1. Analizar la implementación existente.
2. Reutilizar componentes antes de crear nuevos.
3. No duplicar Instrumentos.
4. No duplicar Preguntas.
5. No duplicar Calculadoras.
6. No duplicar Plantillas de Entrevista.
7. Mantener compatibilidad con los módulos consumidores.
8. Crear migraciones únicamente cuando sean necesarias.
9. Mantener la referencia Documento → Instrumento.
10. Mantener versionado de los recursos reutilizables.
11. No utilizar datos personales del documento original como datos de prueba.

No mover recursos fuera de Portafolio.

---

# Validaciones

Después de cambios importantes ejecutar:

- python manage.py check
- Pruebas automatizadas existentes
- Verificar importación de Instrumentos
- Verificar generación de Preguntas
- Verificar Plantillas de Entrevista
- Verificar secciones y orden
- Verificar preguntas condicionales
- Verificar versionado
- Verificar compatibilidad con módulos consumidores
- Verificar que Portafolio no almacene respuestas individuales

---

# Estado Actual

| Componente | Estado |
|------------|--------|
| Documentos | MVP |
| Instrumentos | MVP |
| Preguntas | MVP |
| Calculadoras | SCID-II implementada |
| Plantillas de Entrevista | Pendiente de implementación |
| Plantillas PDF | MVP |
| Reportes | MVP |
| Recursos Compartidos | MVP |
| Servicios Compartidos | En crecimiento |

---

# Regla de Oro

Todo recurso que pueda ser utilizado por dos o más módulos deberá vivir en Portafolio.

La estructura de la Entrevista 1:1 pertenece a Portafolio.

Su aplicación, acceso, respuestas e historial pertenecen a Certificación INTERA.

Los módulos consumidores únicamente deberán consumir los recursos y nunca crear implementaciones paralelas o duplicadas.