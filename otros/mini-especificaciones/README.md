# Especificaciones de Extintores

Documentacion funcional y tecnica para estabilizar y evolucionar la aplicacion `extintores`.

## Alcance

- Incluye la app `extintores`, sus modelos, vistas, formularios, plantillas, JavaScript, CSS, exportaciones y migraciones.
- SQLite se mantiene como base local durante esta etapa.
- La migracion futura a PostgreSQL se tratara como una fase separada.
- `administracion` y `espaciometro` quedan fuera de la implementacion actual, aunque se consideran en los limites de permisos y desacoplamiento.

## Regla de trabajo

Cada cambio debe tener una especificacion, pruebas, criterio de aceptacion y registro en `SEGUIMIENTO.md`. Los cambios funcionales se implementaran por entregas pequenas para validacion manual y commit independiente.

## Documentos

1. `EXT-000-estado-y-alcance.md`
2. `EXT-001-linea-base.md`
3. `EXT-002-integridad-urls-botones-enlaces.md`
4. `EXT-003-intervenciones-y-odt.md`
5. `EXT-004-stock-transaccional.md`
6. `EXT-005-perfiles-y-permisos.md`
7. `EXT-006-estadisticas-y-exportaciones.md`
8. `EXT-007-imagenes-del-servicio.md`
9. `EXT-008-arquitectura-y-frontend.md`
10. `EXT-009-plan-de-pruebas.md`
11. `SEGUIMIENTO.md`

## Estado actual

`EXT-001` tiene registrada la linea base en `EXT-001-linea-base.md`. `EXT-002` y `EXT-003` tambien tienen una especificacion con el mismo identificador que su registro de avance.
