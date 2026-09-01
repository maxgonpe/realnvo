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
