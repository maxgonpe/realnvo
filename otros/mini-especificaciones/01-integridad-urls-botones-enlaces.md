# Integridad de URLs, botones y enlaces

## Requisitos

- Toda URL usada por una plantilla debe generarse con `{% url %}` o con una URL inyectada desde Django.
- No se aceptan `href=""`, `href="#"` ni botones visibles sin accion definida, salvo controles de modal documentados.
- Las acciones que modifican datos deben usar POST, CSRF y validacion de permisos.
- Las acciones destructivas deben tener confirmacion y respuesta visible de exito o error.
- Las rutas de estadisticas no deben tener ambiguedad ni solaparse con parametros genericos.
- Las respuestas AJAX deben comprobar estado HTTP, formato JSON y mostrar errores recuperables.

## Pruebas

- Resolver todas las rutas de `extintores/urls.py` con `reverse()`.
- Renderizar plantillas funcionales y detectar destinos vacios o inexistentes.
- Probar redireccion despues de guardar, eliminar, exportar y volver.
- Probar rutas sin autenticacion y con objetos inexistentes.
- Probar enlaces de PDF y Excel comprobando tipo de contenido.

## Criterios de aceptacion

- Ningun enlace productivo queda sin destino.
- Todas las acciones principales tienen una prueba HTTP.
- Las URLs no dependen de que la aplicacion este montada exclusivamente en `/`.
