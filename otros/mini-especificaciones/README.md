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

1. `00-estado-y-alcance.md`
2. `01-integridad-urls-botones-enlaces.md`
3. `02-intervenciones-y-odt.md`
4. `03-stock-transaccional.md`
5. `04-perfiles-y-permisos.md`
6. `05-estadisticas-y-exportaciones.md`
7. `06-imagenes-del-servicio.md`
8. `07-arquitectura-y-frontend.md`
9. `08-plan-de-pruebas.md`
10. `SEGUIMIENTO.md`

## Estado actual

`EXT-001` tiene registrada la linea base en `EXT-001-linea-base.md`. La compilacion sintactica paso; las comprobaciones Django estan bloqueadas por dependencias no instaladas.
