# Plan de pruebas

## Base

- `python3 manage.py check`
- `python3 manage.py makemigrations --check`
- `python3 manage.py test extintores`

## Capas

1. Modelos: constraints, choices, relaciones y validaciones.
2. Servicios: ODT, stock y estadisticas.
3. Vistas: autenticacion, permisos, redirecciones y errores.
4. URLs y plantillas: reverse, enlaces y formularios.
5. AJAX: JSON, errores, parametros y CSRF cuando corresponda.
6. Exportaciones: contenido y filtros.
7. Navegador: flujos criticos con Playwright cuando la base funcional este estable.

## Criterio de salida por entrega

- Pruebas nuevas verdes.
- No se rompen las pruebas existentes.
- Migraciones consistentes.
- Verificacion manual documentada.
- Commit independiente con alcance claro.
