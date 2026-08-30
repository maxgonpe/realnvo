# Imagenes del servicio

## Necesidad

Cada servicio debe permitir adjuntar como minimo seis imagenes, con posibilidad de ampliar el limite mediante configuracion.

## Alternativas a evaluar

1. Modelo relacionado `ImagenIntervencion`, una imagen por registro. Preferida por escalabilidad.
2. Modelo actual con multiples campos, solo si se demuestra que no limita mantenimiento, validacion ni almacenamiento.

## Requisitos comunes

- Validar extension, MIME, tamano y contenido.
- Mantener orden y descripcion opcional.
- Permitir reemplazar y eliminar con permisos.
- Generar miniaturas sin perder el original.
- Evitar nombres de archivo predecibles y traversal de rutas.
- Proteger el acceso si las imagenes contienen informacion sensible.
- Mantener compatibilidad con imagenes existentes mediante migracion documentada.

La decision se tomara despues de inventariar datos actuales y probar carga, edicion, descarga y rendimiento.

## Implementacion EXT-007-1

- Se creo `ImagenServicio`, con una imagen por registro, orden, descripcion, fecha y usuario.
- Se mantuvo `ImagenIntervencion` para compatibilidad y respaldo temporal.
- La migracion `0031_imagenservicio.py` copia las referencias de `imagen1` a `imagen9` sin mover archivos fisicos.
- En desarrollo se migraron 2.111 referencias y se verifico que las 2.111 tengan archivo existente.
- La sustitucion de formularios, galeria y PDF se hara despues de verificar la migracion en navegador.
- Se registro prueba automatizada del nuevo modelo con orden y descripcion.
- El modelo nuevo queda listo para recibir la integracion de formularios y visualizacion en una siguiente entrega de `EXT-007`.
- La creacion y edicion aceptan multiples archivos mediante `imagenes_nuevas`.
- El detalle y el PDF priorizan el nuevo modelo cuando existen imagenes migradas.
- El modelo antiguo se mantiene como fallback para intervenciones aun no migradas.
- Se agregaron endpoints protegidos para editar descripcion/orden y eliminar imagenes nuevas individualmente.
- La eliminacion borra tambien el archivo asociado del almacenamiento configurado.
- Se agregaron pruebas de edicion y eliminacion individual.

## Validacion manual

- Se registro un servicio con seis fotografias y se verifico su funcionamiento.
- Se agregaron tres fotografias adicionales al mismo servicio y se verifico que tambien funcionaran correctamente.
- La carga multiple, galeria y PDF quedan validados manualmente para el flujo probado.

## Cierre EXT-007

La funcionalidad principal queda completada. El modelo legacy se conserva temporalmente para compatibilidad; su retiro requiere una entrega posterior con respaldo, auditoria y validacion de todos los registros.
