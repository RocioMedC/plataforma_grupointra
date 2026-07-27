---
name: plan-cierre-requerimientos-financieros
---

# Plan: cerrar el 100% del documento de Requerimientos del Sistema Financiero

Fuente: `Requerimientos_Sistema_Financiero_INTRA-2.pdf` (15 páginas, 09/07/2026, solicitante Administración INTRA / Jesús).
Fecha del plan: 2026-07-26. Objetivo: presentar el sistema listo para operar.

Contexto: los 10 criterios de aceptación de la **sección 8** ya estaban cubiertos (ver `DocumentoRequerimentosJesus.md`). Lo que este plan resuelve es todo lo que el documento pide **fuera de esa tabla** — secciones 3, 4, 5, 6, 7 y 9 — más las fallas funcionales detectadas al revisar el código el 2026-07-26.

**Premisa autorizada por el usuario:** el sistema todavía no tiene información real, solo datos de prueba. Se permite cambiar modelos, borrar datos de prueba y refactorizar sin conservar compatibilidad hacia atrás.

---

## 0. Estado: Fases 0 a 5 completadas (2026-07-26)

**16 de los 17 huecos resueltos; el 17º (F7) se descartó porque no era un hueco.** 191 verificaciones automatizadas en verde, repartidas en 5 suites por fase. Commits: `2ad499d` (QA previo), `977ff9c` (F1), `83467cf` (F2), `e860ccd` (F3), `325cecc` (F4), `42f63d7` (F5).

Falta únicamente la **Fase 6**: prueba manual en el navegador (checklist entregada aparte) y despliegue a Railway, ambos pendientes de la confirmación del usuario.

### Desviaciones respecto al plan original (y por qué)

1. **Sellar NO exige método de pago.** El plan decía que `sellar_periodo` fallara si a alguna línea le faltaba el método. Al revisar la captura de referencia de la pág. 6 quedó claro que "Pendiente" **es** un método válido en una nómina ya sellada — de hecho el ejemplo del documento está sellado con $7,037.50 pendiente por dispersar y $0.00 en transferencia y efectivo, justamente porque esas filas están en "Pendiente". Exigirlo habría contradicho el documento.
2. **`LineaNominaSemanal.montos_editados`** (no estaba en el plan). Sin esta bandera, corregir un monto en el borrador y volver a sincronizar hacía que ConsultorioWeb pisara la corrección sin avisar. Lo detectó la prueba de la Fase 2.
3. **F17 se resuelve con confirmación, no con bloqueo duro.** Dos gastos idénticos el mismo día existen de verdad; bloquear en seco dejaba al usuario atorado. Se usa la otra salida que el propio documento contempla ("bloquear una segunda generacion de egreso **o pedir confirmacion**").
4. **F7 descartado** tras confirmar con Jesús que vale de gasolina y bono son el mismo concepto (ver D5).

---

## 1. Diagnóstico: qué falta exactamente

### 🔴 Fallas funcionales (rompen números que ya se muestran)
| # | Problema | Evidencia |
|---|----------|-----------|
| F1 | El método de pago nunca se asigna a los egresos de nómina, y no hay forma de asignarlo desde la UI (solo `/admin/`). Por eso "Pendiente transferencia" y "Pendiente efectivo" del PDF **siempre salen $0**. | `integraciones/importador_nomina.py:50-60`, `honorarios.html:90,102`, `nomina_pdf.html:106,110` |
| F2 | No existe histórico de cambios (usuario, fecha, monto anterior, monto nuevo). `Ajuste` no guarda quién lo hizo ni los montos; los cambios de estatus no dejan rastro. | `models.py:363-389`, `views.py:64-77`, `apps/core/auditoria/` vacío |
| F3 | La pantalla de Recepción ignora su propio filtro de fechas: KPIs, ranking y comparativo usan **todo el histórico**. | `views.py:517` (`CitaRecepcion.objects.all()`) |

### 🟡 Sección 7 completa (estados y botones) — nunca se construyó
| # | Falta | Doc |
|---|-------|-----|
| F4 | Estados **Borrador** y **Sellado** no existen (solo Pendiente/Pagado). | Sec. 7, tabla de estados |
| F5 | Botones "Ver detalle", "Guardar borrador", "Sellar terapeuta/docente", "Sellar periodo". | Sec. 7, tabla de botones |

### 🟡 Detalles por sección
| # | Falta | Doc |
|---|-------|-----|
| F6 | La tabla de cortes no muestra **citas atendidas** ni **ingreso generado** por terapeuta. | Sec. 3 + captura pág. 4 |
| ~~F7~~ | ~~Bono y vale de gasolina están conflacionados.~~ **Descartado 2026-07-26:** Jesús confirmó que vale de gasolina y bono **son lo mismo**. El mapeo actual era correcto y coincide con la tabla 3.1 del doc (Monto base / Vale / Bono-extra). Solo queda mejorar las etiquetas. | Sec. 3.1 |
| F8 | El sellado ocurre en ConsultorioWeb y el portal **importa a mano**; el doc pide que el egreso se guarde automáticamente al sellar. | Sec. 3 |
| F9 | Falta tipo de nómina **quincenal** y **administrativa**; la columna "Tipo" está fija en "Terapeuta". | Sec. 4; `nomina_pdf.html:82-83` |
| F10 | Falta **fecha de pago** en el PDF. | Sec. 4 + captura pág. 6 |
| F11 | Falta columna **Observaciones** en el PDF. | Captura pág. 6 |
| F12 | Recepción no reporta **pacientes** (únicos atendidos). | Sec. 5, criterio 6 |
| F13 | Falta filtro por **terapeuta** en Recepción. | Captura pág. 8 |
| F14 | El catálogo de maestros no se puede **filtrar por nombre**. | Sec. 6.1 |
| F15 | El PDF de Academia no trae **usuario que genera** ni **fecha de pago**. | Sec. 6.1, "Formato sugerido" |
| F16 | No hay consolidado de Academia por periodo con **total general** de todos los docentes. | Sec. 6.1, "Totales" |
| F17 | Un Egreso capturado a mano puede duplicarse (no usa `existe_duplicado`). | Sec. 2, "Regla general" |

---

## 2. Decisiones de diseño (leer antes de codificar)

**D1 — El "sellado" pertenece a la nómina, no a cada egreso.**
La tabla de estados de la sección 7 describe el ciclo de vida de *una nómina*: se captura en Borrador, se sella, y al sellar nacen los egresos. Por eso se crea una **cabecera de nómina semanal** (`NominaSemanal`) con sus líneas, en vez de meter estados Borrador/Sellado dentro de `Egreso`. Los egresos siguen con Pendiente/Pagado, que es lo que significan para el flujo del dinero.

**D2 — La importación de ConsultorioWeb ya no crea Egresos directamente.**
Ahora llena una `NominaSemanal` en **Borrador**. Los Egresos se crean al **sellar** (por terapeuta o por periodo). Esto es lo que el documento pide literalmente ("Al presionar Sellar / Aprobar, guardar automáticamente el egreso en Finanzas") y de paso arregla F1: el método de pago se elige en la línea, antes de sellar.

**D3 — Nómina administrativa y quincenal se capturan a mano, en la misma pantalla.**
`NominaSemanal.tipo` = semanal / quincenal / administrativa. Las semanales se llenan por sincronización; quincenal y administrativa se capturan con un modal (persona + concepto + montos). El PDF es el mismo para las tres.

**D4 — "Ingreso generado" por terapeuta sale del cruce con Recepción.**
La API de ConsultorioWeb ya entrega `total_sesiones` (= citas atendidas) y `detalles` (desglose por paciente) → resuelve F6 y "Ver detalle" **sin tocar el repo de ConsultorioWeb**. El ingreso de clínica no viene en el payload, así que se calcula como la suma de `CitaRecepcion.costo` de ese terapeuta en el rango, con estatus "Sí asistió". Si Recepción no está sincronizada para ese periodo, la columna muestra "—" con un aviso, en vez de mentir con $0.

**D5 — Son 3 conceptos separados, no 4** (confirmado con Jesús el 2026-07-26: *vale de gasolina y bono son lo mismo*). La línea guarda `pago_base`, `vale_gasolina` (etiqueta visible: "Vale de gasolina / bono") y `extras` (etiqueta: "Bono extra / otros autorizados"), y los tres son **editables antes de sellar**. La importación precarga `subtotal_sesiones → pago_base`, `total_bonos → vale_gasolina`, `total_pago - subtotal - bonos → extras`. Coincide con la tabla 3.1 del documento (Monto base / Vale / Bono-extra) y con la captura de la pág. 6.

**D6 — Solo PDF, no PNG.**
El documento dice "imagen **o** PDF". Generar PNG en el servidor exigiría dependencias de sistema (navegador headless / cairo) que complican el despliegue en Railway. Se conserva `xhtml2pdf` y el botón se etiqueta "Descargar PDF (listo para enviar)". Decisión consciente, se documenta como tal.

**D7 — La auditoría vive en `apps/core/auditoria/`**, no en Finanzas: es el RF-19 del portal y la van a necesitar los módulos que siguen (RH, clínico). Finanzas solo la consume y le pone una pantalla de consulta.

**D8 — El sellado en ConsultorioWeb no dispara un webhook todavía.**
Para no tocar un segundo repo la víspera de la presentación, la pantalla de Nómina **sincroniza sola al abrirse** (si la API está configurada), y conserva el botón "Sincronizar ahora". Efecto para el usuario: entra a Finanzas y la nómina ya está ahí, sin doble captura. El webhook queda como mejora posterior, documentada.

---

## 3. Fases

### Fase 0 — Preparación (30 min)
- [x] Commitear el trabajo pendiente en el árbol (13 archivos: correcciones de QA, `apps/core/middleware.py`, expiración de sesión). Va como commit propio antes de empezar, para que el refactor no se mezcle con esas correcciones.
- [x] Confirmar que `python manage.py migrate` corre limpio y el servidor levanta.
- [x] Limpiar datos de prueba que el flujo nuevo va a regenerar: `Egreso.objects.filter(referencia_externa__startswith='consultorioweb:').delete()`. Se hace con un script en el scratchpad, no con un comando de management (es de una sola vez).

### Fase 1 — Auditoría e historial de cambios (F2) — *base de todo lo demás*
**`apps/core/auditoria/models.py`** (nuevo)
- [x] Modelo `RegistroAuditoria`: `usuario` (FK a `AUTH_USER_MODEL`, `SET_NULL`), `fecha` (`auto_now_add`), `content_type` + `object_id` + `registro` (generic FK), `descripcion_objeto` (CharField — copia del `str()` al momento del cambio, para que la bitácora siga siendo legible si el registro se borra), `accion` (creó / modificó / selló / ajustó / importó), `campo`, `valor_anterior`, `valor_nuevo` (CharField, ambos opcionales). Índice por `fecha` y por `content_type+object_id`.
- [x] Migración `apps/core/migrations/0002_registroauditoria.py`.

**`apps/core/auditoria/registro.py`** (nuevo)
- [x] `registrar(usuario, objeto, accion, campo='', anterior='', nuevo='')` — helper único. Nunca lanza excepción hacia arriba: si la auditoría falla, se registra en el log pero **no tumba la operación de negocio**.
- [x] `historial_de(objeto)` — consulta para pintar el historial de un registro.

**Enganchar el helper** (todas las escrituras que cambian dinero o estado):
- [x] `views.py::_actualizar_estatus_simple` — estatus de Egreso, Honorario, Donativo.
- [x] `views.py::ingresos_view` — cambio de estatus / `monto_pagado` de Ingreso.
- [x] Sellado de líneas y de periodo (Fase 2).
- [x] `ajustes.py::registrar_ajuste`.
- [x] `nomina_academia.py::capturar_nomina_academia` y el sellado de Academia (Fase 4).
- [x] Importación/sincronización (un registro por corrida, con el resumen, no uno por fila).

**`Ajuste` mejorado**
- [x] Agregar campos `usuario` (FK, `SET_NULL`), `monto_anterior`, `monto_nuevo` (calculados al registrar: anterior = total del registro original, nuevo = anterior + diferencia). `diferencia` se conserva.
- [x] `registrar_ajuste()` recibe `usuario` y lo guarda.
- [x] `AjusteForm` / `ajustes_view` pasan `request.user`.
- [x] Migración.

**Pantalla de bitácora**
- [x] Vista `bitacora_view` (`finanzas/bitacora/`) protegida por `acceso_finanzas_requerido`: tabla de últimos 200 movimientos (fecha, usuario, acción, registro, campo, antes → después), con filtro por rango de fechas y por tipo de registro. Liga en el sidebar de `_base.html`.

### Fase 2 — Nómina semanal con cabecera, estados y sellado (F1, F4, F5, F6, F7, F8, F9, F10, F11)
Es la fase más grande. Todo lo demás depende poco de ella, así que si se atrasa, se puede terminar sola.

**Modelos nuevos (`apps/finanzas/models.py`)**
- [x] `NominaSemanal`: `tipo` (semanal / quincenal / administrativa), `fecha_inicio`, `fecha_fin`, `fecha_pago` (opcional hasta sellar), `estado` (borrador / sellado), `usuario_genera` (FK, `SET_NULL`), `sellada_en`, `creado_en`. `unique_together = (tipo, fecha_inicio, fecha_fin)` — no se pueden abrir dos nóminas del mismo tipo y periodo.
- [x] `LineaNominaSemanal`: `nomina` (FK), `persona`, `tipo_persona` (terapeuta / administrativo), `concepto` (texto, default "Pago a terapeuta"), `citas_atendidas` (int), `ingreso_generado` (decimal, informativo), `pago_base`, `bono`, `vale_gasolina`, `extras` (los 4 separados, D5), `metodo_pago` (transferencia / efectivo / pendiente), `estatus_pago` (pendiente / pagado), `observaciones`, `referencia_corte` (id del corte de ConsultorioWeb, para dedupe), `sellada` (bool), `sellada_en`, `detalle_json` (el `detalles` de la API, para el "Ver detalle"). `unique_together = (nomina, persona)`.
  - Propiedad `total` = suma de los 4 conceptos.
- [x] `Egreso`: agregar FK opcional `linea_nomina` → `LineaNominaSemanal` (`SET_NULL`), para trazabilidad egreso ↔ nómina (resuelve el campo "Periodo" de la sección 3.1, que hoy solo vive dentro del texto del concepto).
- [x] Migración.

**`apps/finanzas/nomina_semanal.py`** (nuevo — reemplaza a `integraciones/importador_nomina.py` como capa de negocio)
- [x] `sincronizar_nomina(fecha_inicio, fecha_fin, usuario)`: llama a la API, filtra por `ESTATUS_IMPORTABLES`, y hace upsert de la `NominaSemanal` en Borrador y sus líneas. **Nunca sobreescribe una línea ya sellada** (regla de duplicidad de la sección 3.1). Precarga `citas_atendidas = total_sesiones`, `detalle_json = detalles`, y los montos según D5.
- [x] `calcular_ingreso_generado(persona, fecha_inicio, fecha_fin)`: suma `CitaRecepcion.costo` con estatus "Sí asistió" (D4); regresa `None` si no hay citas sincronizadas de ese periodo.
- [x] `sellar_linea(linea, usuario)`: valida que no esté sellada y que tenga método de pago; crea **un Egreso por cada concepto con monto > 0** (base, bono, vale, extras), con `referencia_externa` legible tipo `NOM-2026-07-09-JA-base` (formato del ejemplo de la sección 3.1) y `linea_nomina` apuntando a la línea; marca `sellada=True`; registra en auditoría. Idempotente y atómica.
- [x] `sellar_periodo(nomina, usuario)`: sella todas las líneas no selladas; si alguna no tiene método de pago, **no sella nada** y devuelve la lista de faltantes (mensaje claro); al terminar pone la nómina en Sellado, fija `fecha_pago` y `sellada_en`.
- [x] Borrar `integraciones/importador_nomina.py` y `reportes_nomina.py` (su función la absorbe la cabecera). Quitar sus imports en `views.py`.

**Vistas y UI**
- [x] `nomina_view` reescrita: selector de periodo + tipo; **auto-sincroniza al abrir** si la API está configurada (D8) y hay tipo semanal; tabla de líneas con columnas Persona, Tipo, Citas atendidas, Ingreso generado, Pago base, Bono, Vale, Extras, Total, Método (selector inline), Estatus, Observaciones, y acciones "Ver detalle" / "Sellar".
- [x] Acciones POST: `guardar_borrador` (guarda métodos/montos/observaciones editados en bloque), `sellar_linea`, `sellar_periodo`, `sincronizar`, `estatus_pago` (marcar pagado un egreso ya sellado).
- [x] `nomina_detalle_view` (`nomina/<id>/linea/<id>/`) o modal con el desglose por paciente desde `detalle_json` (fecha, paciente, servicio, monto) — es el botón "Ver detalle" de la sección 7.
- [x] Modal "Capturar nómina manual" para quincenal/administrativa (D3): persona, tipo, concepto, los 4 montos, método, observaciones.
- [x] Banner de estado: Borrador (editable) vs Sellada (solo lectura + descarga).

**PDF renovado (`nomina_pdf.html` + `nomina_descargar_view`)**
- [x] Encabezado: logo, **tipo de nómina** (F9), periodo, **fecha de pago** (F10), badge de estado real Borrador/Sellada (F4), y **usuario que genera**.
- [x] Tabla por persona con la columna **Tipo** real (Terapeuta / Administrativo) y **Observaciones** (F11); las 4 columnas de montos separadas (F7).
- [x] Totales: pendiente por dispersar, pendiente transferencia, pendiente efectivo, vales/extras pendientes — ahora sí con valores reales porque el método de pago ya se captura (F1).
- [x] Detalle de vales por persona (se conserva) + fecha y hora de generación (se conserva).
- [x] La descarga se hace por `NominaSemanal`, no por rango suelto de fechas: `nomina/<id>/descargar/`.

**Ajustes**
- [x] `AjusteForm` acepta también `LineaNominaSemanal` como registro a corregir.
- [x] `_egresos_efectivos` y el resto de helpers del tablero siguen funcionando (los egresos solo existen ya sellados, así que no hay que excluir borradores: verificar).

### Fase 3 — Reporte de Recepción (F3, F12, F13)
- [x] `reporte_recepcion_view`: aplicar el rango de fechas **y** un filtro por terapeuta a `citas` antes de calcular KPIs, ranking, comparativo y tabla. Hoy se ignoran (`views.py:517`).
- [x] KPI nuevo **"Pacientes atendidos"** = `values('paciente').distinct().count()` sobre citas con "Sí asistió" en el rango (F12).
- [x] Selector de terapeuta poblado con los terapeutas presentes en `CitaRecepcion` (F13).
- [x] Que el rango del filtro y el de sincronización sean el mismo control, para que no haya dos campos de fecha que hagan cosas distintas en la misma pantalla.

### Fase 4 — Nómina Academia (F14, F15, F16)
- [x] `NominaAcademia`: agregar `usuario_genera` (FK, `SET_NULL`), `fecha_pago`, y `estado` (borrador / sellado) para alinearla con la nómina semanal. Migración.
- [x] La captura sigue siendo de un paso, pero ahora deja la nómina en **Borrador**; botón "Sellar" que genera los Egresos (hoy se generan en la captura). Así "Sellar docente" existe de verdad (F5) y se puede corregir antes de sellar sin necesidad de un Ajuste.
- [x] Buscador de maestros por nombre en el modal: `<input list="maestros">` + `<datalist>` (HTML puro, sin JS ni dependencias) (F14).
- [x] `nomina_academia_pdf.html`: agregar **usuario que genera** y **fecha de pago** al encabezado (F15).
- [x] Vista + PDF **consolidado de periodo** (`nomina-academia/periodo/<anio>/<mes>/descargar/`): todos los docentes del mes, con total por docente, total transferencia, total efectivo, pendiente y **total general** (F16). Botón "Sellar periodo" que sella todas las nóminas en borrador de ese mes.

### Fase 5 — Cierres finales (F17, D6)
- [x] `EgresoForm`: usar `existe_duplicado(Egreso, persona=..., concepto=..., fecha=...)` y rechazar con mensaje que apunte a la pantalla de Ajustes (F17).
- [x] Revisar que los botones de descarga digan "Descargar PDF (listo para enviar)" (D6) y documentar en el propio plan que no habrá PNG.
- [x] Repasar el sidebar: Tablero, Ingresos, Egresos/Honorarios, Nómina, Nómina Academia, Recepción, Ajustes, Bitácora, Configuración, Donativos, Reportes. Que ninguna pantalla quede huérfana.
- [x] Actualizar `CLAUDE.md`: modelos nuevos, el flujo Borrador→Sellado, y que `apps/core/auditoria/` ya no está vacío.

### Fase 6 — Pruebas y despliegue
- [ ] Pruebas extremo a extremo vía Django test client con el permiso real, por cada fase (mínimo: sincronizar → editar métodos en borrador → sellar una línea → verificar Egresos separados → intentar sellar dos veces → sellar periodo → descargar PDF → registrar ajuste → ver bitácora).
- [ ] Verificar los totales del PDF a mano contra los datos capturados (el punto que hoy sale $0).
- [ ] Checklist de prueba manual en el navegador, entregada como Artifact para que el usuario la recorra.
- [ ] `railway up` en CentralizacionIntra + verificar migraciones aplicadas y las pantallas respondiendo 200.
- [ ] Limpiar datos de prueba en producción antes de la presentación.

---

## 4. Orden de ejecución sugerido

1. **Fase 0** (preparación) — bloqueante, 30 min.
2. **Fase 1** (auditoría) — la usan las fases 2 y 4, va primero.
3. **Fase 2** (nómina semanal) — la más grande y la de mayor impacto en la demo.
4. **Fase 3** (recepción) — independiente, se puede intercalar si la 2 se atora.
5. **Fase 4** (Academia).
6. **Fase 5** (cierres) y **Fase 6** (pruebas + deploy).

Si el tiempo se comprime, el orden de sacrificio es: F16 (consolidado de Academia) → F9 (nómina administrativa/quincenal) → la pantalla de bitácora (el registro se sigue guardando aunque no haya pantalla). **No sacrificar** F1 ni F2: son los dos que el documento pide explícitamente y que hoy fallan.

---

## 5. Archivos afectados

**Nuevos**
- `apps/core/auditoria/models.py`, `apps/core/auditoria/registro.py`
- `apps/core/migrations/0002_registroauditoria.py`
- `apps/finanzas/nomina_semanal.py`
- `apps/finanzas/templates/finanzas/bitacora.html`
- `apps/finanzas/templates/finanzas/nomina_academia_periodo_pdf.html`
- Migraciones de finanzas `0008_*` y siguientes.

**Modificados**
- `apps/finanzas/models.py`, `views.py`, `forms.py`, `urls.py`, `ajustes.py`, `nomina_academia.py`, `admin.py`
- `apps/finanzas/templates/finanzas/`: `_base.html`, `nomina.html`, `nomina_pdf.html`, `nomina_academia.html`, `nomina_academia_pdf.html`, `reporte_recepcion.html`, `honorarios.html`
- `apps/finanzas/static/finanzas/css/finanzas.css`
- `config/settings.py` (nada nuevo previsto; solo si aparece alguna variable)
- `CLAUDE.md`

**Eliminados**
- `apps/finanzas/integraciones/importador_nomina.py`
- `apps/finanzas/reportes_nomina.py`

---

## 6. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| El refactor de nómina rompe el Tablero o Reportes (que suman Egresos). | Los Egresos siguen existiendo con la misma forma; solo cambia **cuándo** nacen. Verificar `_egresos_efectivos` y las gráficas del tablero explícitamente en las pruebas. |
| Migraciones con datos de prueba en Railway. | Los datos son descartables; si una migración se complica, se limpia la tabla afectada. Correr las migraciones en local primero. |
| El "ingreso generado" queda vacío si Recepción no está sincronizada del mismo periodo. | Mostrar "—" con aviso, nunca $0. Es información complementaria, no bloquea el sellado. |
| Auto-sincronizar al abrir la pantalla hace lenta la carga si la API tarda. | `timeout=10` ya está en el cliente; si falla, se muestra la nómina en borrador que ya exista y un aviso, sin error 500. |
| Alcance grande para un día. | El orden de sacrificio de la sección 4 está definido de antemano. |

---

## 7. Preguntas para Jesús (no bloquean, pero conviene confirmar antes de la presentación)

1. **`total_bonos` de ConsultorioWeb: ¿es el vale de gasolina o el bono?** El documento los pide separados y hoy el código asume que es el vale. De la respuesta depende cómo se precargan las columnas (D5). Mientras tanto son editables antes de sellar, así que el usuario puede corregirlo.
2. **Fecha de pago:** ¿se captura al sellar la nómina, o es siempre un día fijo respecto al fin de periodo (ej. el miércoles siguiente)?
3. **Nómina administrativa:** ¿qué conceptos maneja y quién la captura? Por ahora queda como captura manual libre.
4. **Nómina quincenal / prenómina:** en la captura de la pág. 6 aparece "Prenómina quincenal" mezclada con pagos semanales en el mismo documento. ¿Es una nómina aparte o son conceptos dentro de la semanal?
5. **Bitácora:** ¿quién debe poder verla — solo Dirección y Sistemas, o todo el grupo Finanzas? Hoy el plan la deja para todo Finanzas.
