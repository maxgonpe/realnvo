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
]