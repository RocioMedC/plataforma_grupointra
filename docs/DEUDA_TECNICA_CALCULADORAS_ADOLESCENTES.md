# Deuda técnica: calculadoras adolescentes pendientes

## SCID-II adolescentes

La calculadora provisional conserva conteos administrativos, validación de edad
cuando existe fecha de nacimiento y las limitaciones explícitas del protocolo.
El resultado sigue siendo de revisión profesional y no diagnóstico.

### Propuesta de esquema

Crear una entidad relacional `ReglaPreguntaInstrumento`, asociada a
`PreguntaInstrumento`, en lugar de incorporar reglas clínicas en un JSON
genérico. Cada regla requerirá:

| Campo | Tipo | Origen en Excel | Uso |
| --- | --- | --- | --- |
| `tipo` | `CharField` con opciones | Columna o tabla de reglas | Distingue omisión por edad, visibilidad, alerta, revisión e interpretación. |
| `edad_min` / `edad_max` | `PositiveSmallIntegerField`, nulos | Regla de edad | Determina si la pregunta se muestra o excluye. |
| `pregunta_disparadora` | `ForeignKey` a pregunta del mismo instrumento, nulo | Condición fuente | Expresa dependencias entre reactivos. |
| `operador` / `valor_esperado` | `CharField` | Condición fuente | Evalúa la condición declarada sin inferirla. |
| `nivel_revision` | `CharField` con opciones | Alerta o revisión fuente | Señala la revisión administrativa o clínica necesaria. |
| `mensaje_interno` | `TextField` | Nota de fuente | Conserva la instrucción para personal autorizado. |
| `origen_excel` / `orden` | `CharField` y `PositiveIntegerField` | Hoja y fila | Aporta trazabilidad y orden estable. |

La importación debe leer una hoja explícita de reglas, validar que sus claves
pertenezcan al instrumento y aplicar `update_or_create` por pregunta, tipo y
orden. En una reimportación se deben actualizar solo las reglas de la misma
versión y preservar las revisiones históricas publicadas. La calculadora
consumirá estas reglas antes de contar respuestas, registrará omisiones y
alertas en el detalle y nunca generará diagnóstico ni acciones automáticas.

La implementación requerirá una migración de esquema, una migración de datos
para versiones ya importadas y pruebas de importación, edad, visibilidad,
alertas, reimportación y ausencia de diagnóstico.

## Plutchik adolescentes

La calculadora es `ORIENTATIVA`: detecta y deja trazabilidad de los reactivos
críticos 13, 14 y 15, pero no ejecuta acciones externas. Antes de automatizar
un protocolo institucional deberán aprobarse y documentarse:

- criterio de identificación de un «Sí» crítico en los reactivos 13, 14 o 15;
- mensaje aprobado que verá el participante;
- usuario o rol receptor de la alerta y su medio de notificación;
- tiempo máximo de atención, escalamiento y manejo fuera de horario;
- contacto institucional de emergencia;
- registro de lectura, acciones realizadas y trazabilidad en bitácora;
- restricciones de acceso, consentimiento y privacidad.

No deberán inventarse contactos, mensajes clínicos ni automatizaciones antes de
esa aprobación. Las pruebas futuras deberán confirmar entrega de alertas solo a
los roles aprobados, bitácora completa y ausencia de exposición de respuestas
sensibles.
