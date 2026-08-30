# EXT-001 - Linea base tecnica

## Objetivo

Registrar el estado verificable del proyecto antes de iniciar cambios funcionales en `extintores`.

## Fecha

2026-08-29

## Entorno detectado

- Python: `3.11.2`.
- `pip`: disponible en `/home/maxgonpe/extintores/env`.
- Django: `5.2.1`.
- Entorno virtual: `/home/maxgonpe/extintores/env`.
- PostgreSQL: cliente `psql` disponible, pero no se verifico conexion.
- Configuracion local: `myproject/local_settings.py` sobrescribe la base a PostgreSQL.
- Base SQLite presente: `db.sqlite3`, pero no es la base seleccionada por la configuracion local actual.

## Comandos ejecutados

| Comando | Resultado |
|---|---|
| `source /home/maxgonpe/extintores/env/bin/activate && python manage.py check` | Correcto: 0 problemas |
| `source /home/maxgonpe/extintores/env/bin/activate && python manage.py makemigrations --check --dry-run` | Detecta migracion pendiente de `django_summernote` |
| `source /home/maxgonpe/extintores/env/bin/activate && python manage.py test extintores` | Correcto, pero encontro 0 tests |
| `python3 -m compileall -q extintores` | Correcto |
| `python3 -m compileall -q myproject` | Correcto |
| `git diff --check` | Correcto |

## Hallazgos de la linea base

1. Existe un entorno virtual externo funcional en `/home/maxgonpe/extintores/env`.
2. `manage.py check` no reporta problemas.
3. La configuracion local selecciona PostgreSQL y las migraciones de `extintores` estan aplicadas.
4. `makemigrations --check` detecta una migracion pendiente de la dependencia `django_summernote`, no de `extintores`.
5. `python manage.py test extintores` termina correctamente, pero no hay tests implementados.
6. La compilacion sintactica de `extintores` y `myproject` no presenta errores.
7. El estado Git previo a esta entrega contenia unicamente `otros/mini-especificaciones/` como cambios no versionados.

## Criterio de cierre

La entrega queda funcionalmente cerrada: el entorno permite ejecutar la aplicacion y `check` pasa. Queda una incidencia tecnica abierta por la migracion pendiente de `django_summernote` y una deuda de pruebas porque `extintores` no contiene tests ejecutables.

## Siguiente accion

Resolver o documentar la migracion pendiente de `django_summernote` y comenzar `EXT-002` con la primera suite de integridad de URLs, botones y enlaces.
