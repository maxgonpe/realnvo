# Stock transaccional

## Regla de negocio

El stock disponible nunca puede ser negativo. Antes de consumir, el sistema debe validar la cantidad disponible y mostrar al usuario producto, cantidad solicitada y saldo actual. Si no alcanza, no debe guardar ninguna parte de la operacion.

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
- Consumo superior al saldo, sin cambios persistidos.
- Dos consumos concurrentes.
- Edicion de cantidad y cambio de producto.
- Eliminacion y devolucion.
- Reenvio de formulario.
- Integridad despues de una excepcion.

## Implementacion inicial

- Se creo `extintores/services/stock.py` con operaciones atomicas y bloqueo de producto.
- Los consumos rechazan cantidades superiores al saldo disponible mediante `StockInsuficiente`.
- Los ingresos, ediciones y eliminaciones de compras usan el servicio y se revierten dentro de transacciones.
- `ItemIntervencion.save/delete` y `DetalleIngreso.save` ya no modifican stock implicitamente.
- Se cubrieron saldo insuficiente, consumo, eliminacion y ausencia de efectos secundarios del modelo.
- La gestion de `ItemOdt` se mantiene pendiente de integrar completamente al mismo flujo y de agregar feedback de error en sus vistas.
