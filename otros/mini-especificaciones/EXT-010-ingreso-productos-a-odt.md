# Ingreso de productos a ODT

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

El stock insuficiente sigue bloqueando la operacion completa y muestra el mensaje al usuario. Se agrego prueba de producto sin precio.

Verificacion actual: 46 tests de `extintores`, `check` y `diff --check` correctos.

## Mensajes visibles de stock

Se comprobo que la vista capturaba correctamente `StockInsuficiente`, pero el template base no renderizaba el framework de mensajes de Django. Como consecuencia, la operacion se revertia silenciosamente para el usuario. Se agrego en `base.html` un bloque accesible de alertas (`aria-live` y `role="alert"`) para mostrar el producto, stock disponible y cantidad solicitada.

Como refuerzo, el error capturado tambien se envia directamente como `error_stock` a `odt/agregar_productos.html`, que lo muestra dentro de la pagina y explica que la seleccion no fue agregada. Este mensaje no depende de JavaScript ni de una redireccion.

## Regla ODT sin restriccion de stock

Por requerimiento operativo, los flujos de agregar y modificar productos en ODT ya no llaman al servicio de ajuste de inventario. Las cantidades, asociaciones, precios y subtotales se procesan sin bloquearse por stock. Esta excepcion aplica solo a ODT; los consumos de intervenciones y movimientos de inventario mantienen sus controles.

## Incidente: varias necesidades seleccionadas

Cuando varias filas seleccionadas usaban el mismo producto, `get_or_create()` encontraba el mismo `ItemOdt` y la vista reemplazaba la cantidad acumulada por la cantidad de la ultima fila. Se corrigio para sumar cada cantidad seleccionada al `ItemOdt` existente y descontar solo la cantidad nueva del stock. Esto aplica tanto a servicios ilimitados como a productos con stock finito, dentro de la misma transaccion.
