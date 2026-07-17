from django.urls import path

from . import views

urlpatterns = [
    path(
        "rendiciones/desde-imagen/",
        views.rendicion_desde_imagen,
        name="adm_rendicion_desde_imagen",
    ),
    path(
        "rendiciones/<int:pk>/",
        views.rendicion_resumen,
        name="adm_rendicion_resumen",
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
]
