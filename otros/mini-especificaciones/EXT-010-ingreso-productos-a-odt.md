# Ingreso de productos a ODT

> **Decision funcional vigente:** Recarga y Mantencion no consumen stock. Las demas categorias consumen la cantidad indicada y pueden dejar saldos negativos para ajuste posterior de inventario.

## Incidente

La pantalla `ODT-EDITAR` no mostraba productos ya asociados en desarrollo ni en produccion.

## Diagnostico

`ItemOdtFormSet` es un `inlineformset_factory` relacionado con `Odt`. En la rama GET de `editar_odt` se inicializaba con `queryset=odt.items.all()`, pero sin `instance=odt`. La comprobacion real reprodujo que el formset entregaba cero formularios con `queryset` y los items existentes con `instance=odt`.

## Correccion

Se cambio la inicializacion GET a:

```python
ItemOdtFormSet(instance=odt, prefix='itemodt_set')
```

La correccion no cambia las asociaciones, el stock ni el procesamiento POST. Solo permite que el formset cargue los `ItemOdt` pertenecientes a la ODT.

## Verificacion

- Se agrego una prueba que crea una ODT con un `ItemOdt` y confirma que el formset lo carga.
- La suite de `extintores` debe permanecer verde.
- En produccion se debe actualizar el codigo y reiniciar los workers antes de probar `ODT-EDITAR`.

## Incidencia ODT-EDITAR

La ODT `65` tenia 11 `ItemOdt` y una imagen en su intervencion asociada, pero `ODT-EDITAR` no mostraba los productos. El template iteraba `itemset_con_subtotales`, variable que la vista no enviaba al contexto. Se corrigio construyendo ese contexto desde los formularios del formset y se agrego una referencia visible al numero de registros de imagen asociados.

Verificacion: 45 tests de `extintores`, `check` y `diff --check` correctos.

## Incidente en produccion: precio vacio

En `odt/111/agregar-productos/` la seleccion de un producto sin `precio_unitario` provocaba `TypeError` al guardar el `ItemOdt`. El modelo calculaba el subtotal multiplicando la cantidad por `None`.

Se corrigio `ItemOdt.save()` para usar precio `0` cuando el precio del producto esta vacio. Tambien se corrigio el guardado de cantidades existentes para recalcular precio y subtotal, y la vista informa cuando no se selecciona ningun producto valido.

El stock insuficiente ya no bloquea las operaciones: las categorias finitas pueden quedar con saldo negativo y se registra la cantidad completa solicitada.

Verificacion actual: 46 tests de `extintores`, `check` y `diff --check` correctos.

## Mensajes visibles de stock

Se comprobo que la vista capturaba correctamente `StockInsuficiente`, pero el template base no renderizaba el framework de mensajes de Django. Como consecuencia, la operacion se revertia silenciosamente para el usuario. Se agrego en `base.html` un bloque accesible de alertas (`aria-live` y `role="alert"`) para mostrar el producto, stock disponible y cantidad solicitada.

Como refuerzo, el error capturado tambien se envia directamente como `error_stock` a `odt/agregar_productos.html`, que lo muestra dentro de la pagina y explica que la seleccion no fue agregada. Este mensaje no depende de JavaScript ni de una redireccion.

## Regla de stock por categoria

Por requerimiento operativo, ODT e intervenciones usan el servicio de stock. Recarga y Mantencion no modifican stock; las categorias finitas descuentan cantidades y permiten saldos negativos sin bloquear la operacion.

### Alcance y advertencia futura

- Aplica a ODT y consumos de intervenciones.
- Recarga y Mantencion no modifican stock, aunque tengan `None` o `0`.
- Las categorias finitas modifican stock y pueden dejar saldos negativos.
- La cantidad completa queda registrada, aunque el saldo resultante sea negativo.
- Si en el futuro se requiere descontar inventario desde ODT, debe definirse primero el momento exacto del descuento, la reversa, la edicion, la eliminacion y el tratamiento de servicios ilimitados.

### Historial del incidente

1. `agregar-productos` lanzaba `StockInsuficiente` sin mostrar el motivo al usuario; se agrego manejo transaccional y mensajes visibles.
2. Productos sin precio provocaban `TypeError` al calcular el subtotal; se establecio precio y subtotal `0` como fallback.
3. Varias necesidades con el mismo producto sobrescribian la cantidad; ahora se acumulan.
4. `ODT-EDITAR` no mostraba productos existentes porque el inline formset no recibia `instance=odt`; se corrigio la carga.
5. Se comprobo que ODT e intervenciones deben usar el mismo criterio: servicios ilimitados sin movimiento de stock y categorias finitas con saldos negativos permitidos.

## Incidente: varias necesidades seleccionadas

Cuando varias filas seleccionadas usan el mismo producto, `get_or_create()` encuentra el mismo `ItemOdt` y la vista suma cada cantidad nueva. El stock se ajusta solo por la cantidad agregada y las operaciones se mantienen dentro de la misma transaccion.
