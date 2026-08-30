# Seguimiento de construccion

Estado actual: **EXT-003 completada; nomenclatura normalizada**.

| ID | Entrega | Estado | Evidencia | Bloqueos |
|---|---|---|---|---|
| EXT-001 | Inventario y linea base | Completada | `EXT-001-linea-base.md`; `check` correcto; migraciones extintores aplicadas | Migracion pendiente de `django_summernote`; tests iniciales aun no existian |
| EXT-002 | URLs, botones y enlaces | Completada | 5 tests; `check`; `git diff --check` correctos | Exportaciones estadisticas pendientes en EXT-006 |
| EXT-003 | Intervencion y ODT | Completada | Migracion 0028 aplicada; 8 tests y `check` correctos | Pendiente definir UX de desvinculacion |
| EXT-004 | Stock transaccional | En progreso | Servicio atomico y 3 tests nuevos; suite total: 11 tests | Integrar completamente ItemOdt y feedback de errores |
| EXT-005 | Perfiles y permisos | En progreso | Checklist, roles base, permisos por area y 9 tests nuevos; suite total: 19 tests | Validar UX manual y revisar permisos de cada boton |
| EXT-006 | Estadisticas y exportaciones | Pendiente | Dataset de referencia y exportaciones | Definir indicadores prioritarios |
| EXT-007 | Imagenes del servicio | Pendiente | Decision tecnica y prueba de migracion | Inventario de imagenes actuales |
| EXT-008 | Arquitectura y frontend | Pendiente | Regresion funcional | Comparar vistas legacy |
| EXT-009 | Plan de pruebas y regresion | Pendiente | Suite completa y reporte | Estabilizacion previa |

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
- Se retiraron los enlaces Excel/PDF que tenian `href` vacio; se implementaran con destinos reales en `EXT-006`.
- Las busquedas AJAX de clientes y productos usan nombres de URL Django.
- Se agregaron cinco tests de rutas y plantillas en `extintores/tests.py`.
- Verificacion: `python manage.py test extintores` paso con 5 tests.
- Verificacion: `python manage.py check` paso sin problemas.
- Verificacion: `git diff --check` paso sin problemas.

## Registro EXT-003

- Se hizo opcional la asociacion ODT-Intervencion sin romper la relacion uno a uno.
- Las ODT independientes se conservan al eliminar una intervencion mediante `SET_NULL`.
- Se elimino la creacion automatica duplicada del signal.
- Se genero y aplico `extintores/migrations/0028_alter_odt_intervencion.py`.
- `python manage.py check` paso sin problemas.
- La suite crea y destruye la base temporal correctamente; 8 tests pasan.
- La base de pruebas ya pudo crearse; se corrigio un error real del historial cuando la intervencion no tiene alias.

## Registro EXT-004

- Se creo el servicio transaccional `extintores/services/stock.py`.
- Se bloqueo el stock negativo y se agrego el error de dominio `StockInsuficiente`.
- Se retiro la modificacion implicita de stock desde `ItemIntervencion` y `DetalleIngreso`.
- Ingresos nuevos, ediciones y eliminaciones aplican movimientos dentro de `transaction.atomic()`.
- Verificacion: `python manage.py test extintores` paso con 11 tests.
- Verificacion: `python manage.py check` paso sin problemas.
- `makemigrations --check` aun reporta una migracion pendiente de `django_summernote`, dependencia externa.

## Registro EXT-005

- Se agregaron permisos funcionales de usuarios, permisos, firma y datos financieros.
- Se creo la migracion `0029_alter_intervencion_options.py`.
- Se separo la capacidad de firma del rol administrativo mediante `TechnicianProfile`.
- Se elimino el hardcode del usuario `andres` en la gestion de usuarios.
- Se agregaron roles combinables como grupos Django.
- Verificacion: `python manage.py migrate extintores` correcto.
- Verificacion: `python manage.py test extintores` paso con 13 tests.
- Verificacion: `python manage.py check` correcto.

## Actualizacion EXT-005

- La pantalla de usuarios permite asignar roles combinables y permisos individuales.
- La pantalla permite activar o retirar el perfil tecnico de cada usuario.
- Los roles se crean de forma dinamica al ser seleccionados.
- Verificacion: `python manage.py test extintores` paso con 14 tests.

## Actualizacion EXT-005-2

- Todas las rutas funcionales de `extintores` quedan protegidas contra acceso anonimo.
- La asignacion de roles crea grupos y sus permisos base.
- Se agrego prueba de redireccion al login para una ruta protegida.
- Verificacion: `python manage.py test extintores` paso con 15 tests.

## Actualizacion EXT-005-3

- Se aplicaron permisos por area a las rutas de operaciones, catalogo, inventario y reportes.
- Se agrego la migracion `0030_alter_intervencion_options.py`.
- Se corrigio el orden de decoradores para diferenciar `302` anonimo de `403` sin permiso.
- Verificacion: `python manage.py migrate extintores` correcto.
- Verificacion: `python manage.py test extintores` paso con 15 tests.

## Actualizacion EXT-005-4

- Se completaron las rutas de ODT, clientes, catalogo, factores, stock, exportaciones y alertas.
- Se agrego prueba de usuario autenticado sin permiso funcional (`403`).
- Verificacion: `python manage.py test extintores` paso con 16 tests.
- Verificacion: `python manage.py check` paso sin problemas.

## Actualizacion EXT-005-5

- Se agregaron pruebas de matriz para tecnico e inventario.
- Se verifico que tecnico pueda operar sin administrar catalogo.
- Se verifico que inventario pueda gestionar stock sin crear intervenciones.
- Verificacion: `python manage.py test extintores` paso con 18 tests.

## Actualizacion EXT-005-6

- Se elimino la visibilidad de Usuarios basada en el nombre `andres`.
- La plantilla usa el permiso `extintores.manage_users` para mostrar ese control.
- Verificacion: `python manage.py test extintores` paso con 19 tests.

## Actualizacion EXT-005-7

- Se creo `extintores/templates/403.html` como respuesta amigable para permisos insuficientes.
- El template informa la restriccion, el permiso requerido y ofrece volver al inicio o atras.
- Se mantiene el codigo HTTP `403` y los usuarios anonimos siguen siendo redirigidos al login.
- Verificacion: `python manage.py test extintores` paso con 19 tests.
