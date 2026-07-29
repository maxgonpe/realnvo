from django.urls import path

from . import views

urlpatterns = [
    # A007 — Panel del módulo
    path("", views.panel_administracion, name="adm_panel"),
    # ------------------------------------------------------------------
    # Rendiciones (R001–R022) — activas + esqueleto workflow
    # ------------------------------------------------------------------
    path("rendiciones/", views.rendicion_lista, name="adm_rendicion_lista"),
    path("rendiciones/nueva/", views.rendicion_crear, name="adm_rendicion_crear"),
    path(
        "rendiciones/dashboard/",
        views.rendicion_dashboard,
        name="adm_rendicion_dashboard",
    ),
    path(
        "rendiciones/responsables/",
        views.responsable_lista,
        name="adm_responsable_lista",
    ),
    path(
        "rendiciones/responsables/nuevo/",
        views.responsable_crear,
        name="adm_responsable_crear",
    ),
    path(
        "rendiciones/responsables/<int:pk>/",
        views.responsable_detalle,
        name="adm_responsable_detalle",
    ),
    path(
        "rendiciones/responsables/<int:pk>/editar/",
        views.responsable_editar,
        name="adm_responsable_editar",
    ),
    path(
        "rendiciones/responsables/<int:pk>/activar/",
        views.responsable_activar,
        name="adm_responsable_activar",
    ),
    path(
        "rendiciones/responsables/<int:pk>/desactivar/",
        views.responsable_desactivar,
        name="adm_responsable_desactivar",
    ),
    path(
        "rendiciones/categorias/",
        views.categoria_lista,
        name="adm_categoria_lista",
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
        "rendiciones/<int:pk>/excel/",
        views.rendicion_export_excel,
        name="adm_rendicion_excel",
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
        "rendiciones/<int:pk>/entrega-fondo/",
        views.entrega_fondo_crear,
        name="adm_entrega_fondo_crear",
    ),
    path(
        "rendiciones/<int:pk>/presentar/",
        views.rendicion_presentar,
        name="adm_rendicion_presentar",
    ),
    path(
        "rendiciones/<int:pk>/revisar/",
        views.rendicion_revisar,
        name="adm_rendicion_revisar",
    ),
    path(
        "rendiciones/<int:pk>/aprobar/",
        views.rendicion_aprobar,
        name="adm_rendicion_aprobar",
    ),
    path(
        "rendiciones/<int:pk>/liquidar/",
        views.rendicion_liquidar,
        name="adm_rendicion_liquidar",
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
    # ------------------------------------------------------------------
    # Banco / conciliación (B001–B021) — esqueleto
    # ------------------------------------------------------------------
    path("bancos/", views.banco_lista, name="adm_banco_lista"),
    path("bancos/nuevo/", views.banco_crear, name="adm_banco_crear"),
    path("bancos/<int:pk>/", views.banco_detalle, name="adm_banco_detalle"),
    path("bancos/<int:pk>/editar/", views.banco_editar, name="adm_banco_editar"),
    path("bancos/<int:pk>/clave/", views.banco_clave, name="adm_banco_clave"),
    path("bancos/<int:pk>/activar/", views.banco_activar, name="adm_banco_activar"),
    path(
        "bancos/<int:pk>/desactivar/",
        views.banco_desactivar,
        name="adm_banco_desactivar",
    ),
    path("cuentas/", views.cuenta_lista, name="adm_cuenta_lista"),
    path("cuentas/nueva/", views.cuenta_crear, name="adm_cuenta_crear"),
    path(
        "cuentas/desde-cartola/",
        views.cuenta_desde_cartola,
        name="adm_cuenta_desde_cartola",
    ),
    path("cuentas/<int:pk>/", views.cuenta_detalle, name="adm_cuenta_detalle"),
    path("cuentas/<int:pk>/editar/", views.cuenta_editar, name="adm_cuenta_editar"),
    path("cuentas/<int:pk>/activar/", views.cuenta_activar, name="adm_cuenta_activar"),
    path(
        "cuentas/<int:pk>/desactivar/",
        views.cuenta_desactivar,
        name="adm_cuenta_desactivar",
    ),
    path("cartolas/importar/", views.cartola_importar, name="adm_cartola_importar"),
    path("cartolas/<int:pk>/", views.cartola_detalle, name="adm_cartola_detalle"),
    path(
        "plantillas-cartola/",
        views.plantilla_mapeo_lista,
        name="adm_plantilla_mapeo_lista",
    ),
    path(
        "plantillas-cartola/nueva/",
        views.plantilla_mapeo_crear,
        name="adm_plantilla_mapeo_crear",
    ),
    path(
        "plantillas-cartola/<int:pk>/",
        views.plantilla_mapeo_detalle,
        name="adm_plantilla_mapeo_detalle",
    ),
    path(
        "plantillas-cartola/<int:pk>/editar/",
        views.plantilla_mapeo_editar,
        name="adm_plantilla_mapeo_editar",
    ),
    path(
        "plantillas-cartola/<int:pk>/probar/",
        views.plantilla_mapeo_probar,
        name="adm_plantilla_mapeo_probar",
    ),
    path(
        "plantillas-cartola/<int:pk>/activar/",
        views.plantilla_mapeo_activar,
        name="adm_plantilla_mapeo_activar",
    ),
    path(
        "plantillas-cartola/<int:pk>/desactivar/",
        views.plantilla_mapeo_desactivar,
        name="adm_plantilla_mapeo_desactivar",
    ),
    # Compatibilidad con ruta esqueleto anterior
    path(
        "plantillas-mapeo/",
        views.plantilla_mapeo_lista,
        name="adm_plantilla_mapeo_lista_legacy",
    ),
    path("movimientos/", views.movimiento_lista, name="adm_movimiento_lista"),
    path(
        "movimientos/<int:pk>/",
        views.movimiento_detalle,
        name="adm_movimiento_detalle",
    ),
    path(
        "movimientos/<int:pk>/clasificar/",
        views.movimiento_clasificar,
        name="adm_movimiento_clasificar",
    ),
    path(
        "movimientos/<int:pk>/clasificaciones/",
        views.movimiento_historial_clasificaciones,
        name="adm_movimiento_historial_clasificaciones",
    ),
    path(
        "conciliacion/",
        views.conciliacion_dashboard,
        name="adm_conciliacion_dashboard",
    ),
    # ------------------------------------------------------------------
    # Facturación / cobranza (F001–F014) — esqueleto
    # ------------------------------------------------------------------
    path("facturas/", views.factura_lista, name="adm_factura_lista"),
    path("facturas/nueva/", views.factura_crear, name="adm_factura_crear"),
    path("pagos/nuevo/", views.pago_crear, name="adm_pago_crear"),
    path("cobranza/", views.cobranza_lista, name="adm_cobranza_lista"),
    path(
        "cobranza/antiguedad/",
        views.antiguedad_saldos,
        name="adm_antiguedad_saldos",
    ),
    # ------------------------------------------------------------------
    # Factoring (X001–X013) — esqueleto
    # ------------------------------------------------------------------
    path(
        "factoring/empresas/",
        views.empresa_factoring_lista,
        name="adm_empresa_factoring_lista",
    ),
    path(
        "factoring/operaciones/",
        views.operacion_lista,
        name="adm_operacion_factoring_lista",
    ),
    path(
        "factoring/operaciones/<int:pk>/",
        views.operacion_detalle,
        name="adm_operacion_factoring_detalle",
    ),
    path(
        "factoring/reportes/",
        views.factoring_reportes,
        name="adm_factoring_reportes",
    ),
]
