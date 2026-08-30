# Perfiles y permisos

## Perfiles

- `administrador`: acceso total y configuracion.
- `supervisor`: operacion, revision y reportes autorizados.
- `tecnico`: intervenciones y datos operativos necesarios, sin informacion financiera.
- `inventario`: productos, entradas, consumos y stock.
- `solo_lectura`: consultas y reportes permitidos.

## Matriz inicial

| Area | Administrador | Supervisor | Tecnico | Inventario | Solo lectura |
|---|---|---|---|---|---|
| Intervenciones | CRUD | CRUD | crear/editar propias | lectura | lectura |
| ODT | CRUD | CRUD | lectura/actualizacion operativa | lectura | lectura |
| Clientes | CRUD | CRUD | lectura limitada | lectura | lectura |
| Productos | CRUD | CRUD | lectura | CRUD stock | lectura |
| Estadisticas operativas | si | si | propias/permitidas | si | si |
| Datos financieros futuros | si | segun permiso | no | no | no |
| Usuarios y permisos | si | no | no | no | no |

Los permisos deben implementarse con grupos y permisos Django, no con nombres de usuario hardcodeados. La matriz se versiona antes de habilitar nuevas areas.

## Pruebas

Cada ruta de lectura, escritura, eliminacion y exportacion debe probarse con los cinco perfiles.
