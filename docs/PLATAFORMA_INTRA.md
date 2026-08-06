# PLATAFORMA_INTRA.md

# Plataforma INTRA

## Propósito

Plataforma INTRA es una plataforma modular donde cada módulo administra exclusivamente su propio dominio de negocio y reutiliza recursos compartidos cuando corresponde.

Los módulos deben permanecer desacoplados y comunicarse mediante servicios bien definidos.

---

# Módulos

## Portafolio

Biblioteca institucional de recursos reutilizables.

Responsable de:

- Documentos
- Instrumentos
- Preguntas
- Calculadoras
- Plantillas PDF
- Reportes
- Recursos Compartidos
- Servicios Compartidos

Todos los módulos consumen estos recursos desde Portafolio.

---

## Certificación INTERA

Responsable de:

- Escuelas
- Procesos de Certificación
- Configuración de Instrumentos
- Aplicaciones
- Participantes
- Respuestas
- Resultados
- Entrevistas
- Consejerías
- Canalizaciones
- Bitácora

Consume Instrumentos, Preguntas y Calculadoras desde Portafolio.

---

## Finanzas

Módulo encargado de la gestión financiera.

Actualmente en desarrollo.

---

## CRM de Ventas

Módulo encargado de la gestión comercial.

Actualmente en desarrollo.

---

## Consultorio Web

Sistema independiente.

Responsable de:

- Recepción
- Pacientes
- Agenda
- Expediente Clínico
- Atención Terapéutica

No forma parte de Plataforma INTRA.

La comunicación será únicamente mediante API.

---

# Arquitectura General

```text
                  Plataforma INTRA

        ┌────────────┬────────────┬────────────┐

        │            │            │

   Portafolio     INTERA        CRM

        │

        │ API

        ▼

  Consultorio Web
```

---

# Principios de Arquitectura

- Un único propietario por cada dominio.
- No duplicar modelos entre módulos.
- No duplicar lógica de negocio.
- Reutilizar componentes antes de crear nuevos.
- Comunicación entre sistemas mediante API.
- Mantener independencia entre módulos.
- Mantener compatibilidad hacia atrás.

---

# Reglas Obligatorias

- Instrumentos pertenecen a Portafolio.
- Preguntas pertenecen a Portafolio.
- Calculadoras pertenecen a Portafolio.
- INTERA nunca administra Instrumentos.
- Portafolio nunca administra procesos de negocio.
- Consultorio Web administra únicamente procesos clínicos.
- No acceder directamente a bases de datos de otros sistemas.
- No crear dependencias circulares.
- No romper funcionalidades existentes.

---

# Restricciones de Arquitectura

- No duplicar Instrumentos.
- No duplicar Preguntas.
- No duplicar Calculadoras.
- No mover recursos compartidos fuera de Portafolio.
- No implementar lógica clínica dentro de Plataforma INTRA.
- No modificar Consultorio Web fuera de la capa de integración.
- No reconstruir componentes funcionales sin necesidad.

---

# Lineamientos de Desarrollo

Antes de realizar cualquier cambio:

1. Leer este documento.
2. Leer el archivo `.md` del módulo correspondiente.
3. Analizar la implementación existente.
4. Reutilizar componentes antes de crear nuevos.
5. Mantener compatibilidad con el sistema actual.
6. Crear migraciones únicamente cuando sean necesarias.
7. Ejecutar las validaciones correspondientes al finalizar.

Si una regla de negocio no está documentada, no asumir el comportamiento. Reportarlo antes de implementarlo.

---

# Validaciones

Después de cambios importantes ejecutar:

- `python manage.py check`
- Pruebas automatizadas existentes.
- Verificar URLs.
- Verificar migraciones.
- Verificar compatibilidad con funcionalidades existentes.

---

# Estado Actual

| Módulo | Estado |
|---------|--------|
| Portafolio | MVP |
| Certificación INTERA | MVP funcional |
| CRM | Desarrollo |
| Finanzas | Desarrollo |
| Consultorio Web | Sistema independiente |

---

# Regla de Oro

Antes de desarrollar cualquier componente responder:

**¿Este recurso pertenece realmente a este módulo o debería implementarse como un componente reutilizable para toda Plataforma INTRA?**

Si puede ser reutilizado por más de un módulo, deberá desarrollarse como un recurso compartido y no como una implementación específica.