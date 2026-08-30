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

## Implementacion inicial EXT-008

- Se extrajo el JavaScript global de temas desde `base.html` a `static/extintores/js/theme.js`.
- El script valida temas permitidos antes de modificar clases o `localStorage`.
- `base.html` es el layout activo y carga el recurso mediante `{% static %}`.
- La extraccion no cambia el comportamiento visual esperado.
- Se agregaron pruebas para verificar la carga del recurso y la lista segura de temas.
- Se corrigio la inicializacion para DOM ya cargado y se agrego versionado de cache `?v=3`.
- Se extrajo el filtro comun de tarjetas a `static/extintores/js/card-filter.js`.
- Se extrajo la busqueda de productos y el formset de ingresos a `static/extintores/js/producto-formset.js`; las plantillas ya no mantienen respaldo inline.
- Se extrajo el autocompletado de clientes a `static/extintores/js/cliente-autocomplete.js`; la logica especifica de formsets de intervencion permanece en la plantilla.
- Se extrajo la busqueda de ODT a `static/extintores/js/odt-search.js`, cancelando solicitudes anteriores y mostrando estados de error/carga.
- Se extrajo la busqueda de intervenciones a `static/extintores/js/intervencion-search.js`, manteniendo la URL AJAX inyectada por Django.
- Se escaparon valores introducidos por usuario en la previsualizacion de extintores y resultados de clientes antes de insertarlos en el DOM.
- `editar_consumos.html` usa `producto-formset.js` para la parte comun y `consumo-formset.js` para validaciones especificas de stock y sincronizacion del formulario.
- Se extrajeron los dos formsets y controles de desplazamiento de `odt/editar.html` a `static/extintores/js/odt-formset.js`.
- Se extrajeron los formsets configurables de `odt/editar-general.html` a `static/extintores/js/odt-general-formsets.js` mediante atributos `data-*`.
- Se centralizaron los formsets simples y controles de desplazamiento de `intervenciones/editar.html` y `editar_intervencion.html`.
- Se extrajo la galeria, lightbox, filtro y navegacion de `detalle_intervencion.html` a `static/extintores/js/detalle-intervencion.js`.
- Se reemplazaron los `print()` de `views.py` por `logging`, conservando mensajes de validacion como `warning` y diagnostico como `debug`.
- La auditoria de imports y `urls.py` confirma que las rutas activas importan exclusivamente desde `views.py`; `views_fin.py` y `viewsjulio.py` quedan pendientes de retirada tras regresion comparativa.
- La aplicacion no usa actualmente `highcharts` ni `fusioncharts`; ambos componentes legacy fueron retirados durante `EXT-009`, junto con `django-braces`.
- Regresion tecnica de cierre: 43 tests globales, `check`, `diff --check`, `findstatic` y `collectstatic` correctos.
- Cierre manual: temas, formularios, galerias y busquedas verificadas en navegador; stock finito, servicios ilimitados y errores de stock validados.
- Validacion manual realizada: temas, stock insuficiente, Mantencion y Recarga con `stock=None`; Recarga 40/75/100% se muestra y registra sin descontar inventario.
- El despliegue de recursos estaticos requiere ejecutar `collectstatic` en cada servidor.
