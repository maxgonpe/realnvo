# Estado y alcance

## Objetivo

Hacer que la aplicacion de servicios de extintores sea consistente, segura, comprobable y eficiente sin iniciar aun el desarrollo de Administracion ni Espaciometro.

## Decisiones confirmadas

- Una ODT puede existir de forma independiente.
- Una intervencion puede tener una ODT asociada cuando el proceso la requiera.
- Nunca se debe crear una ODT implicita o duplicada sin una decision explicita del flujo.
- El stock no puede quedar negativo.
- Las operaciones que excedan el stock deben advertir y bloquear el consumo antes de persistirlo.
- Perfiles objetivo: administrador, supervisor, tecnico, inventario y solo lectura.
- Los permisos deben aislar futuras areas financieras de tecnicos y perfiles no autorizados.
- Estadisticas: filtros, agrupaciones, comparaciones y exportaciones PDF/Excel cuando los datos lo permitan.
- La solucion de imagenes debe soportar al menos seis imagenes por servicio y queda abierta a estudio.

## Fuera de alcance inmediato

- Implementacion de `administracion`.
- Cambios funcionales en `espaciometro`.
- Migracion local de SQLite a PostgreSQL.
- Rediseño visual completo sin relacion con integridad o usabilidad.

## Orden de entregas

1. Integridad de URLs, formularios, botones y enlaces.
2. Intervencion y ODT.
3. Stock.
4. Permisos.
5. Estadisticas y exportaciones.
6. Imagenes.
7. Refactor y rendimiento.
8. Regresion y preparacion de despliegue.
