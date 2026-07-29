# Control de avance — módulo Administración

Fuente: `otros/adm-pdf/` (Gantt XML + mini-especificaciones en `_extracted/`).
Última actualización: 2026-07-29 — **B008 Clasificación manual.**

Leyenda: `hecho` | `parcial` | `esqueleto` | `pendiente`

## Cómo usar este archivo

1. Elegir la siguiente tarea Gantt del orden del plan técnico.
2. Implementar el **corte vertical** (modelo → servicio → form → vista → URL → template → prueba).
3. Actualizar la fila correspondiente aquí (`esqueleto` → `parcial`/`hecho`).
4. Anotar gaps de modelo en `models_pendientes.py` si aparecen.

## Iteración 0 — Fundaciones

| Trabajo | Estado | Notas |
|--------|--------|-------|
| Estructura services/selectors/forms/views/templates/tests | hecho | Paquetes creados |
| Cablear URLs del esqueleto | hecho | `administracion/urls.py` |
| Panel A007 + menú base | hecho | `/administracion/` |
| Matriz permisos A004 (códigos) | parcial | `permissions.py` stub |
| Auditoría A005 | pendiente | TODO en services/transversal |
| Adjuntos protegidos A006 | pendiente | Ver models_pendientes |
| Factories de prueba | esqueleto | `tests/factories.py` |
| Separar models.py en paquete | pendiente | Opcional |

## Iteración 1 — Maestros y cabecera

| Código | Tarea | Estado | Dónde mirar |
|--------|-------|--------|-------------|
| **R003** | **Responsables** | **hecho** | `services/rendiciones.py`, `views/transversal.py`, `/administracion/rendiciones/responsables/` |
| R004 | Categorías y subcategorías | esqueleto | Siguiente corte rendiciones |
| R002 | Crear y editar rendición | parcial | Crear activo; falta snapshot responsable / edición formal |
| R001 | Lista y búsqueda | parcial | Lista activa; falta filtros avanzados vía selector |

### R003 — detalle del corte

- Modelo: `ResponsableRendicion` (+ `area`, `correo`, `telefono`)
- Servicio: crear / actualizar / activar / desactivar + RUT normalizado y único entre activos
- Selector: listado con búsqueda y resumen
- URLs: lista, nuevo, detalle, editar, activar, desactivar
- UI: anclada en panel Administración y pestaña Extintores

## Rendiciones (resto)

| Código | Tarea | Estado |
|--------|-------|--------|
| R005 | Entregas de fondo | esqueleto |
| R006 | Detalle de gastos | parcial (escritorio/OCR) |
| R007 | Adjuntos | parcial / gap modelo |
| R008 | Validación documental | pendiente |
| R009 | Cálculos | parcial |
| R010 | Presentación | esqueleto |
| R011 | Revisión | esqueleto |
| R012 | Aprobación | esqueleto |
| R013 | Historial | pendiente |
| R014 | Liquidación | esqueleto |
| R015 | Devolución | pendiente |
| R016 | Reembolso | pendiente |
| R017 | Conciliación liquidación | pendiente |
| R018 | Alertas | pendiente |
| R019 | Export PDF/Excel | parcial (PDF activo; Excel esqueleto) |
| R020 | Dashboard | esqueleto |
| R021 | Pruebas | pendiente |
| R022 | Manual | pendiente |

## Banco / conciliación

| Código | Estado | Notas |
|--------|--------|-------|
| **B001** | **hecho** | CRUD bancos + clave cartola cifrada + verificar PDF |
| **B002** | **hecho** | CRUD cuentas + titular + carga desde cartola PDF |
| **B003** | **hecho** | Import PDF → CartolaBancaria + MovimientoBancario (enteros) |
| **B004** | **hecho** | Plantillas + parser PDF por banco + versionado |
| **B005** | **hecho** | Archivo / exacto / en-archivo / posibles + UI análisis |
| **B006–B007** | **hecho** | Lista/detalle movimientos |
| **B008** | **hecho** | Clasificación + historial + permisos conciliado |
| B018 | esqueleto | URL+template |
| B009–B017, B019–B021 | pendiente | |

### B001 — detalle del corte

- CRUD: lista / nuevo / detalle / editar / activar / desactivar
- Clave PDF: formulario aparte (nunca se muestra); Fernet derivado de `SECRET_KEY`
- Verificación opcional contra PDF de muestra
- Bancos semilla: Estado, Falabella, de Chile (claves cifradas en BD)

### B002 — detalle del corte

- Campo `titular` + CRUD completo de cuentas
- Carga desde cartola PDF (`/administracion/cuentas/desde-cartola/`) usando clave B001
- Heurísticas por banco (Estado CuentaRUT, Falabella, Chile)
- Panel/nav: verde = operativo, ámbar = parcial, gris = esqueleto

### B003 — detalle del corte

- Modelo `CartolaBancaria` (cabecera: saldos/totales enteros)
- `MovimientoBancario` con `monto`/`cargo`/`abono`/`saldo` como **enteros** (sin decimales)
- Parsers PDF: Estado / Falabella / Chile (`services/parsers_cartola_pdf.py`)
- Importación: `/administracion/cartolas/importar/` → crea importación + cartola + movimientos
- Plantillas PDF con `parser_codigo`, `fecha_sin_anio`, separador decimal vacío
- Anti-duplicado por SHA-256 de archivo y fingerprint por movimiento

### B005 — detalle del corte

- Servicio `services/duplicados.py`: fingerprint, archivo SHA-256, lote `__in`, posibles
- Códigos: `ARCHIVO_DUPLICADO`, `DUPLICADO_EXACTO`, `DUPLICADO_EN_ARCHIVO`, `POSIBLE_DUPLICADO`
- UI en `/administracion/cartolas/importar/`: acción Analizar (sin guardar) vs Importar
- Reimportar el mismo PDF muestra enlace a la importación previa
- Posibles duplicados se importan con advertencia (MVP); exactos se omiten
- `IntegrityError` concurrente capturado como duplicado omitido

### B008 — detalle del corte

- Modelo `ClasificacionMovimientoBancario` (una activa por movimiento; historial)
- Categorías filtradas por dirección INGRESO/EGRESO; OTRO exige observación
- Servicio `services/clasificacion_movimientos.py` con `select_for_update`
- No altera tipo/monto/descripción bancarios ni estado de conciliación
- Reclasificar movimiento conciliado: permiso especial + observación obligatoria
- URLs: `/movimientos/<pk>/clasificar/` y `/movimientos/<pk>/clasificaciones/`
- Detalle B007 muestra clasificación activa y enlace a reclasificar

### B004 — detalle del corte

- Modelos: `PlantillaMapeoCartola`, `CampoMapeoCartola` (+ FK/contadores en `ImportacionCartola`)
- Servicio: crear / actualizar (nueva versión si ya se usó) / activar / desactivar / validar esquema / previsualizar
- Selector: listado filtrable + resumen de validación
- URLs: `/administracion/plantillas-cartola/` (+ nueva, detalle, editar, probar, activar, desactivar)
- Reglas: FECHA_OPERACION + DESCRIPCION + esquema A/B/C monetario

## Facturación / cobranza

| Código | Estado |
|--------|--------|
| F002, F003, F005, F010, F012 | esqueleto |
| resto F | pendiente |

## Factoring

| Código | Estado |
|--------|--------|
| X001, X002, X003, X012 | esqueleto |
| resto X | pendiente |

## Próximo paso recomendado

**B009 — Aplicaciones bancarias múltiples** (distribuir monto entre destinos del sistema).
