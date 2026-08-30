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
