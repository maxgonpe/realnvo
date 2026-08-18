from django.urls import path

from . import views


app_name = "espaciometro"


urlpatterns = [

    # Dashboard
    path(
        "",
        views.dashboard,
        name="dashboard",
    ),

    # ESP002 + ESP003
    path(
        "estructura/",
        views.estructura,
        name="estructura",
    ),

    # ESP004
    path(
        "medir/",
        views.ejecutar_medicion,
        name="ejecutar_medicion",
    ),

    # ESP005
    path(
        "rutas/",
        views.configurar_rutas,
        name="configurar_rutas",
    ),

    path(
        "rutas/guardar/",
        views.guardar_rutas,
        name="guardar_rutas",
    ),

    # ESP006
    path(
        "tipos/",
        views.configurar_tipos,
        name="configurar_tipos",
    ),

    path(
        "tipos/guardar/",
        views.guardar_tipos,
        name="guardar_tipos",
    ),

    # ESP008
    path(
        "ruta/<int:ruta_id>/",
        views.detalle_ruta,
        name="detalle_ruta",
    ),

    # ESP009
    path(
        "historico/",
        views.historico,
        name="historico",
    ),

    path(
        "ruta/<int:ruta_id>/evolucion/",
        views.evolucion_ruta,
        name="evolucion_ruta",
    ),

    # ESP010
    path(
        "inventario/",
        views.inventario,
        name="inventario",
    ),

    # ESP011
    path(
        "ciclo-vida/",
        views.ciclo_vida,
        name="ciclo_vida",
    ),

        # ESP012
    path(
        "candidatos/",
        views.candidatos,
        name="candidatos",
    ),

    path(
        "candidatos/crear/",
        views.crear_lote_candidatos_view,
        name="crear_lote_candidatos",
    ),

    path(
        "candidatos/lote/<int:lote_id>/",
        views.detalle_lote_candidatos,
        name="detalle_lote_candidatos",
    ),

        # ESP013
    path(
        "respaldos/",
        views.respaldos,
        name="respaldos",
    ),

    path(
        "respaldos/preparar/<int:lote_id>/",
        views.preparar_respaldo,
        name="preparar_respaldo",
    ),

    path(
        "respaldos/<int:respaldo_id>/",
        views.detalle_respaldo,
        name="detalle_respaldo",
    ),

        # ESP014
    path(
        "respaldos/<int:respaldo_id>/descargar/",
        views.descargar_respaldo,
        name="descargar_respaldo",
    ),

    path(
        "respaldos/descargas/<int:descarga_id>/confirmar/",
        views.confirmar_descarga_view,
        name="confirmar_descarga",
    ),

        # ESP015
    path(
        "liberacion/lote/<int:lote_id>/",
        views.evaluar_liberacion_view,
        name="evaluar_liberacion",
    ),

    path(
        "liberacion/lote/<int:lote_id>/ejecutar/",
        views.ejecutar_liberacion_view,
        name="ejecutar_liberacion",
    ),

    path(
        "liberacion/<int:liberacion_id>/",
        views.detalle_liberacion_view,
        name="detalle_liberacion",
    ),

        # ESP015 — retiro del ZIP privado

    path(
        "respaldos/<int:respaldo_id>/retiro-servidor/",
        views.evaluar_retiro_respaldo_view,
        name="evaluar_retiro_respaldo",
    ),

    path(
        "respaldos/<int:respaldo_id>/retiro-servidor/ejecutar/",
        views.ejecutar_retiro_respaldo_view,
        name="ejecutar_retiro_respaldo",
    ),


    # ESP016 — AUDITORÍA
    
    path(
        "auditoria/",
        views.auditoria_view,
        name="auditoria",
    ),

    path(
        "auditoria/lote/<int:lote_id>/",
        views.auditoria_lote_view,
        name="auditoria_lote",
    ),


    # ESP020 — INVENTARIO BASE DE DATOS
    
    path(
        "base-datos/",
        views.base_datos_view,
        name="base_datos",
    ),

    path(
    "base-datos/historico/tomar/",
    views.tomar_fotografia_base_datos_view,
    name="tomar_fotografia_base_datos",
    ),


    path(
        "base-datos/respaldo/crear/",
        views.crear_respaldo_base_datos_view,
        name="crear_respaldo_base_datos",
    ),

    path(
        "base-datos/respaldo/<int:respaldo_id>/descargar/",
        views.descargar_respaldo_base_datos_view,
        name="descargar_respaldo_base_datos",
    ),
    
]