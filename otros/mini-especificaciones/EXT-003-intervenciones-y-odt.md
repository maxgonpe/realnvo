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

## Implementacion EXT-003

- `Odt.intervencion` ahora es opcional y usa `SET_NULL`, permitiendo ODT independientes.
- Se elimino el signal que creaba ODT automaticamente antes de guardar los detalles.
- La creacion explicita permanece en los flujos que solicitan `con_odt`.
- Se agrego la migracion `0028_alter_odt_intervencion.py`.
- Se agregaron pruebas para ODT independiente, intervencion sin ODT e intervencion con ODT explicita.
- Se corrigio el historial para intervenciones sin alias, usando un identificador de respaldo estable.
