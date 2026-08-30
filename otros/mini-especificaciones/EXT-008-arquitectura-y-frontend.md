# Arquitectura y frontend

## Backend

- Separar vistas por contexto: intervenciones, ODT, inventario, clientes, reportes y usuarios.
- Mover reglas de negocio a servicios probables y reutilizables.
- Mantener selectores para consultas complejas.
- Retirar `views_fin.py` y `viewsjulio.py` solo despues de comparar comportamiento y completar regresion.
- Eliminar `print()` de produccion y usar logging.

## Frontend

- Mantener un unico template base activo.
- Extraer JavaScript comun para busquedas, formsets y confirmaciones.
- Usar `textContent` o plantillas seguras en vez de `innerHTML` con datos no confiables.
- Inyectar URLs desde Django.
- Cancelar busquedas anteriores y mostrar estados de carga, vacio y error.
- Mantener accesibilidad basica: labels, foco, teclado y mensajes asociados.
