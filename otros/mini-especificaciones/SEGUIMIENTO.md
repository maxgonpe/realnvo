# Seguimiento de construccion

Estado actual: **EXT-002 completada; pendiente limpiar migracion de dependencia**.

| ID | Entrega | Estado | Evidencia | Bloqueos |
|---|---|---|---|---|
| EXT-001 | Inventario y linea base | Completada | `EXT-001-linea-base.md`; `check` correcto; migraciones extintores aplicadas | Migracion pendiente de `django_summernote`; 0 tests extintores |
| EXT-002 | URLs, botones y enlaces | Completada | 5 tests; `check`; `git diff --check` correctos | Exportaciones estadisticas pendientes en EXT-005 |
| EXT-003 | Intervencion y ODT | Pendiente | Tests de asociacion e idempotencia | Decidir borrado/desvinculacion |
| EXT-004 | Stock transaccional | Pendiente | Tests de saldo, concurrencia y rollback | Inventario historico |
| EXT-005 | Perfiles y permisos | Pendiente | Matriz y tests por perfil | Confirmar permisos de tecnico |
| EXT-006 | Estadisticas y exportaciones | Pendiente | Dataset de referencia y exportaciones | Definir indicadores prioritarios |
| EXT-007 | Imagenes | Pendiente | Decision tecnica y prueba de migracion | Inventario de imagenes actuales |
| EXT-008 | Frontend y refactor | Pendiente | Regresion funcional | Comparar vistas legacy |
| EXT-009 | Pruebas de regresion | Pendiente | Suite completa y reporte | Estabilizacion previa |

## Formato de actualizacion

Para cada entrega registrar:

- fecha;
- archivos modificados;
- comportamiento implementado;
- pruebas ejecutadas y resultado;
- verificacion manual solicitada;
- commit asociado;
- riesgos pendientes.

## Convencion de commits

Usar commits pequenos por entrega, por ejemplo `extintores: corrige integridad de urls` o `extintores: centraliza movimientos de stock`.

## Registro EXT-002

- Se ordeno la ruta fija `/estadisticas/ver/` antes de la ruta parametrizada por mes.
- Se retiraron los enlaces Excel/PDF que tenian `href` vacio; se implementaran con destinos reales en `EXT-005`.
- Las busquedas AJAX de clientes y productos usan nombres de URL Django.
- Se agregaron cinco tests de rutas y plantillas en `extintores/tests.py`.
- Verificacion: `python manage.py test extintores` paso con 5 tests.
- Verificacion: `python manage.py check` paso sin problemas.
- Verificacion: `git diff --check` paso sin problemas.
