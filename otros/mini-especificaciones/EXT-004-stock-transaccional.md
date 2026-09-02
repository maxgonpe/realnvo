# Stock transaccional

## Regla de negocio

Las categorias finitas pueden quedar con stock negativo. Recarga y Mantencion no modifican stock, aunque tengan `None` o `0`; su precio se multiplica directamente por la cantidad. La cantidad ingresada siempre es positiva.

## Diseño requerido

- Centralizar entradas, consumos, devoluciones, anulaciones y ajustes en un servicio.
- Usar `transaction.atomic()` y bloqueo de producto con `select_for_update()`.
- Usar un tipo numerico consistente y cantidades positivas.
- No modificar stock desde `Model.save()` ni `Model.delete()`.
- Registrar referencia, usuario, fecha, delta y saldo resultante.
- Hacer la operacion idempotente para evitar doble descuento por reenvio.
- Al editar una linea, revertir el movimiento anterior y aplicar el nuevo dentro de la misma transaccion.

## Pruebas

- Consumo exacto del saldo.
- Consumo superior al saldo, conservando el saldo negativo.
- Dos consumos concurrentes.
- Edicion de cantidad y cambio de producto.
- Eliminacion y devolucion.
- Reenvio de formulario.
- Integridad despues de una excepcion.

## Implementacion inicial

- Se creo `extintores/services/stock.py` con operaciones atomicas y bloqueo de producto.
- Los consumos permiten cantidades superiores al saldo disponible y conservan el saldo negativo para ajuste posterior.
- Los ingresos, ediciones y eliminaciones de compras usan el servicio y se revierten dentro de transacciones.
- `ItemIntervencion.save/delete` y `DetalleIngreso.save` ya no modifican stock implicitamente.
- Se cubrieron saldo insuficiente, consumo, eliminacion y ausencia de efectos secundarios del modelo.
- ODT e intervenciones usan el mismo criterio por categoria mediante `services/stock.py`.
# Nota de alcance ODT e intervenciones

Las operaciones de productos dentro de una ODT y los consumos de intervenciones comparten la regla por categoria: Recarga y Mantencion no descuentan stock; las categorias finitas descuentan y permiten saldos negativos. Compras, eliminaciones y ajustes conservan la atomicidad y el bloqueo de producto.
