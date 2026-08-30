# Intervenciones y ODT

## Regla de negocio

Una ODT es una entidad independiente. La asociacion con una intervencion es opcional y debe ser explicita. Crear o editar una intervencion no debe crear una ODT automaticamente salvo que el flujo lo solicite.

## Requisitos tecnicos

- Eliminar la duplicidad entre signal y vista.
- Usar una unica relacion y nombre coherente para la asociacion.
- Crear la asociacion dentro de una transaccion cuando el flujo la requiera.
- No copiar detalles parcialmente antes de que los formsets hayan sido validados.
- Mantener la independencia de una ODT creada manualmente.
- Definir comportamiento al eliminar o desvincular una intervencion.

## Pruebas

- Crear intervencion sin ODT.
- Crear intervencion con ODT.
- Crear ODT independiente.
- Editar ambos tipos sin duplicacion.
- Reintentar una misma operacion y comprobar idempotencia.
- Fallar un formset y comprobar que no queda ODT parcial.
