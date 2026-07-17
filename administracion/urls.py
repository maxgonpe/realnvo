from django.urls import path

from . import views

urlpatterns = [
    path(
        "rendiciones/",
        views.rendicion_lista,
        name="adm_rendicion_lista",
    ),
    path(
        "rendiciones/nueva/",
        views.rendicion_crear,
        name="adm_rendicion_crear",
    ),
    path(
        "rendiciones/<int:pk>/",
        views.rendicion_escritorio,
        name="adm_rendicion_escritorio",
    ),
    path(
        "rendiciones/<int:pk>/resumen/",
        views.rendicion_resumen,
        name="adm_rendicion_resumen",
    ),
    path(
        "rendiciones/<int:pk>/agregar/",
        views.rendicion_agregar_comprobante,
        name="adm_rendicion_agregar_comprobante",
    ),
    path(
        "rendiciones/<int:pk>/pdf/",
        views.rendicion_pdf,
        name="adm_rendicion_pdf",
    ),
    path(
        "rendiciones/<int:pk>/finalizar-carga/",
        views.rendicion_finalizar_carga,
        name="adm_rendicion_finalizar_carga",
    ),
    path(
        "rendiciones/<int:pk>/reabrir-carga/",
        views.rendicion_reabrir_carga,
        name="adm_rendicion_reabrir_carga",
    ),
    path(
        "detalles/<int:pk>/editar/",
        views.detalle_editar,
        name="adm_detalle_editar",
    ),
    path(
        "detalles/<int:pk>/eliminar/",
        views.detalle_eliminar,
        name="adm_detalle_eliminar",
    ),
    # Compatibilidad con enlace antiguo del panel
    path(
        "rendiciones/desde-imagen/",
        views.rendicion_desde_imagen,
        name="adm_rendicion_desde_imagen",
    ),
]
