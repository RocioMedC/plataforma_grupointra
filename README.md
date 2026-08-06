# Plataforma Grupo INTRA

## Documentación de arquitectura

Antes de realizar cambios importantes en el proyecto, revisar los documentos en el siguiente orden:

1. `plataforma_intra.md`
2. `portafolio.md`
3. `intera.md`
4. `INTEGRACION_ConsultorioWeb.md`, cuando la tarea involucre Consultorio Web
5. `MODELO_DATOS.md`
6. `UX_GUIDELINES.md`
7. `ROADMAP.md`

## Propósito de cada documento

- `plataforma_intra.md`: arquitectura general y responsabilidades de los módulos.
- `portafolio.md`: recursos compartidos, instrumentos, preguntas y calculadoras.
- `intera.md`: flujo y reglas de Certificación INTERA.
- `INTEGRACION_ConsultorioWeb.md`: comunicación entre Plataforma INTRA y Consultorio Web.
- `MODELO_DATOS.md`: propietario de cada entidad y relaciones principales.
- `UX_GUIDELINES.md`: lineamientos de experiencia de usuario.
- `ROADMAP.md`: alcance actual y próximas fases.

## Reglas generales

- No duplicar modelos ni lógica entre módulos.
- Reutilizar componentes existentes antes de crear nuevos.
- Mantener Portafolio como propietario de los recursos compartidos.
- Mantener Consultorio Web como sistema independiente.
- Realizar integraciones únicamente mediante API.
- No romper funcionalidades, migraciones, URLs ni pruebas existentes.
- No repetir información ya documentada en otro archivo `.md`.

## Validación mínima

Después de cambios importantes ejecutar:

```bash
python manage.py check
python manage.py test