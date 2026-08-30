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

Los botones de descarga que no tenian destino fueron retirados en `EXT-002`. Las exportaciones especificas de estadisticas se implementaran en esta fase, con enlaces reales y pruebas de contenido, antes de volver a exponer esos botones.
