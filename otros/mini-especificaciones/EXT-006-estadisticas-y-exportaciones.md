# Estadisticas y exportaciones

## Objetivo

Ofrecer una vista confiable y flexible del servicio de extintores, evitando calculos duplicados y permitiendo exportar resultados cuando exista una representacion valida.

## Capacidades

- Filtrar por periodo, cliente, tecnico, tipo de servicio, estado, agente, capacidad y producto.
- Agrupar por mes, cliente, tecnico, estado, tipo y producto.
- Comparar periodos.
- Mostrar totales, porcentajes, tendencias y alertas de datos faltantes.
- Exportar el mismo conjunto filtrado a Excel y PDF.
- Incluir fecha de generacion, filtros aplicados y usuario en cada exportacion.
- Usar consultas agregadas y evitar N+1.
- Definir una fuente unica de verdad para los calculos.

## Consistencia

- Los nombres de modelos y campos deben coincidir con el esquema actual.
- Las restricciones unicas deben representar las dimensiones reales del dato.
- Un resultado exportado debe coincidir con el resultado mostrado para los mismos filtros.

## Pruebas

- Dataset pequeno con totales calculados manualmente.
- Filtros combinados y periodos sin datos.
- Comparacion entre meses.
- Validacion del contenido XLSX y del tipo MIME.
- Validacion de PDF no vacio, con titulo, filtros y totales.

## Estado de implementacion

Los botones de descarga que no tenian destino fueron retirados en `EXT-002`. Las exportaciones especificas de estadisticas se implementaran en `EXT-006`, con enlaces reales y pruebas de contenido, antes de volver a exponer esos botones.

## Implementacion inicial EXT-006

- Se agregaron filtros por tipo de intervencion y estado.
- Se agregaron exportaciones reales por mes a Excel y PDF.
- Las exportaciones respetan los mismos filtros enviados por la pantalla.
- Se corrigio la agregacion por estado para usar `Sum('cantidad')` en lugar de contar filas.
- La fuente de detalle utiliza `EstadisticaDetalleExtintor` y conserva el resumen de productos existente.
- Queda pendiente una segunda iteracion para agrupaciones avanzadas, comparaciones de periodos y unificar completamente el calculo historico.
- Los totales de intervenciones y extintores respetan el filtro de tipo seleccionado.
- Los endpoints rechazan meses con formato distinto de `YYYY-MM` con respuesta `400`.
- Se validan exportaciones leyendo el XLSX generado y comprobando la firma PDF.
- La pantalla permite filtrar por cliente, tipo de intervencion, estado, agente y peso.
- Las dimensiones seleccionadas se propagan a Excel y PDF.
- Se agrego prueba de exportacion con filtros combinados.
- Se agrego comparacion opcional contra otro mes con los mismos filtros.
- La comparacion muestra total anterior, diferencia absoluta y variacion porcentual cuando procede.
- Se agrego agrupacion configurable por estado, agente, peso, tipo o cliente.
- Se agrego una visualizacion proporcional basada en los resultados agrupados.
- Las agrupaciones respetan todos los filtros seleccionados y usan `Sum('cantidad')`.
- La regeneracion de un mes elimina el corte anterior antes de reconstruirlo.
- Las ODT independientes no rompen la reconstruccion estadistica.
- La reconstruccion es idempotente para el mismo conjunto de datos.
- Excel puede exportar la agrupacion seleccionada, no solo el detalle plano.
- La agrupacion exportada usa la misma agregacion que la visualizacion.
- PDF tambien puede exportar la agrupacion seleccionada.
- Se agrego una tendencia historica de hasta 12 meses.

## Cierre EXT-006

La especificacion queda implementada para la primera version operativa: filtros, comparacion, agrupaciones, tendencia y exportaciones PDF/Excel tienen rutas funcionales y pruebas automatizadas. Las nuevas metricas de negocio que se definan posteriormente deben incorporarse como una nueva entrega versionada, sin alterar silenciosamente los calculos existentes.
