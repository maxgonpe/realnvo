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

## Decisiones confirmadas

- Por ahora un tecnico puede trabajar sobre cualquier intervencion.
- Esa regla queda preparada para cambiar a intervenciones propias o autorizadas.
- Para firmar basta con tener `TechnicianProfile`; no se exige un permiso adicional.
- Un usuario puede combinar varios roles, por ejemplo administrador y tecnico.
- El administrador puede asignar roles y permisos individuales.
- Los perfiles tendran acceso amplio inicialmente porque la empresa necesita cubrir varias areas.

## Implementacion inicial

- Se agregaron permisos funcionales `manage_users`, `manage_permissions`, `sign_documents` y `view_financial_data`.
- Se creo `extintores/permissions.py` para centralizar la evaluacion.
- La firma se separo del rol: depende de `TechnicianProfile`.
- Se elimino la autorizacion por nombre de usuario `andres`.
- La gestion de usuarios ahora requiere el permiso Django `extintores.manage_users`.
- Los grupos existentes pueden combinarse y recibir permisos desde el admin de Django.
- La pantalla `usuarios_simple` permite asignar roles, permisos individuales y perfil tecnico mediante checklist.
- Los grupos de roles se crean automaticamente al asignarse por primera vez.
- Todas las rutas de `extintores` requieren autenticacion por defecto.
- Los roles administrador, supervisor y tecnico reciben permisos base al ser asignados.
- Las rutas operativas tienen permisos por area: operaciones, catalogo, inventario y reportes.
- Un usuario autenticado sin el permiso funcional recibe `403`; un usuario anonimo recibe redireccion al login.
- Se mantienen preparadas las reglas para restringir en el futuro las intervenciones propias o autorizadas.
- Se cubrieron las rutas restantes de ODT, clientes, catalogo, factores, stock, exportaciones y alertas con permisos de area.
- La interfaz no sustituye la proteccion de backend: las restricciones se aplican tambien al solicitar la URL directamente.
- Los controles de gestion de usuarios ya no dependen de nombres de usuario en las plantillas.
- Las denegaciones para usuarios autenticados muestran `403.html` con explicacion y navegacion segura.

## Pruebas

Cada ruta de lectura, escritura, eliminacion y exportacion debe probarse con los cinco perfiles.
