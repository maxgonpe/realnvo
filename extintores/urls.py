from django.urls import path
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static
from django.utils.timezone import now
from django.shortcuts import redirect
from .views import IntervencionListView, crear_intervencion,\
                   editar_intervencion, detalle_intervencion,\
                   eliminar_intervencion, IntervencionExcel, IntervencionPDF,\
                   OdtListView, editar_odt, odt_detalle,eliminar_odt,\
                   odt_excel, odt_pdf, agregar_cliente,\
                   modificar_cliente, eliminar_cliente,\
                   lista_clientes,agregar_producto,\
                   modificar_producto,eliminar_producto,\
                   lista_productos, consulta_stock_productos, agregar_item_odt, agregar_categoria,\
                   modificar_categoria,eliminar_categoria,lista_categorias,\
                   IntervencionAjaxListView, factorajustecliente_lista,\
                   factorajustecliente_crear, factorajustecliente_editar,\
                   factorajustecliente_eliminar,odt_agregar_productos,\
                   odt_editar_items, ingreso_stock_nuevo, lista_comprado, comprado_editar, comprado_eliminar,\
                   exportar_inventario_pdf, exportar_inventario_excel, generar_estadisticas_view,\
                    generar_estadisticas_mensuales, ver_estadisticas_view,\
                    exportar_estadisticas_excel, exportar_estadisticas_pdf,\
                   alertas_view, editar_consumos_intervencion, buscar_clientes_ajax, buscar_productos_ajax,\
                   usuarios_simple
from .permissions import (
    PERM_GESTIONAR_CATALOGO, PERM_GESTIONAR_INVENTARIO,
    PERM_GESTIONAR_OPERACIONES, PERM_VER_OPERACIONES, PERM_VER_REPORTES,
    requiere_permiso,
)

urlpatterns = [
    path('', IntervencionListView.as_view(), name='intervencion_lista'),
    path('ajax/intervenciones/', IntervencionAjaxListView.as_view(), name='ajax_intervenciones'),
    path('nueva/', crear_intervencion, name='intervencion_crear'),
    path('editar/<int:pk>/', editar_intervencion, name='intervencion_editar'),
    path('eliminar/<int:pk>/', eliminar_intervencion, name='eliminar_intervencion'),
    path('detalle/<int:pk>/', detalle_intervencion, name='intervencion_detalle'),
    path("intervenciones/<int:pk>/consumos/", editar_consumos_intervencion, name="editar_consumos_intervencion"),
    path('excel/<int:pk>/', IntervencionExcel.as_view(), name='intervencion_excel'),
    path('pdf/<int:pk>/', IntervencionPDF.as_view(), name='intervencion_pdf'),
    path('odt/', OdtListView.as_view(), name='odt_lista'),
    path('odt/editar/<int:pk>/', editar_odt, name='odt_editar'),
    path('odt/<int:pk>/', odt_detalle, name='odt_detalle'),
    path("odt/<int:pk>/excel/", odt_excel, name="odt_excel"),
    path("odt-pdf/<int:pk>/pdf/", odt_pdf, name="odt_pdf"),
    path('odt-add/<int:odt_pk>/agregar-item/', agregar_item_odt, name='agregar_item_odt'),
    path('odt-eliminar/<int:pk>/', eliminar_odt, name='eliminar_odt'),
    path('odt/<int:pk>/agregar-productos/', odt_agregar_productos, name='odt_agregar_productos'),
    path('odt/<int:pk>/editar-items/', odt_editar_items, name='odt_editar_items'),
    path('cliente/', lista_clientes, name='lista_clientes'),
    path('cliente/nuevo/', agregar_cliente, name='agregar_cliente'),
    path('cliente/editar/<int:pk>/', modificar_cliente, name='modificar_cliente'),
    path('cliente/eliminar/<int:pk>/', eliminar_cliente, name='eliminar_cliente'),
    path('cliente/alertas/', alertas_view, name='alertas'),
    path('producto/', lista_productos, name='lista_productos'),
    path('producto/nuevo/', agregar_producto, name='agregar_producto'),
    path('producto/editar/<int:pk>/', modificar_producto, name='modificar_producto'),
    path('producto/eliminar/<int:pk>/', eliminar_producto, name='eliminar_producto'),
    path('producto/ingreso/', ingreso_stock_nuevo, name='ingreso_stock_nuevo'),
    path('producto/consulta-stock/', consulta_stock_productos, name='consulta_stock_productos'),
    path('producto/comprado/', lista_comprado, name='comprado_lista'),
    path('producto/comprado/editar/<int:pk>/', comprado_editar, name='comprado_editar'),
    path('producto/comprado/eliminar/<int:pk>/', comprado_eliminar, name='comprado_eliminar'),
    path('productos/inventario/excel/', exportar_inventario_excel, name='inventario_excel'),
    path('productos/inventario/pdf/', exportar_inventario_pdf, name='inventario_pdf'),
    path('categoria/', lista_categorias, name='lista_categorias'),
    path('categoria/nueva/', agregar_categoria, name='agregar_categoria'),
    path('categoria/editar/<int:pk>/', modificar_categoria, name='modificar_categoria'),
    path('categoria/eliminar/<int:pk>/', eliminar_categoria, name='eliminar_categoria'),
    path('factor/lista', factorajustecliente_lista, name='factorajustecliente_lista'),
    path('factor/nuevo/', factorajustecliente_crear, name='factorajustecliente_crear'),
    path('factor/<int:pk>/editar/', factorajustecliente_editar, name='factorajustecliente_editar'),
    path('factor/<int:pk>/eliminar/', factorajustecliente_eliminar, name='factorajustecliente_eliminar'),
    path('estadisticas/generar/', generar_estadisticas_view, name='generar_estadisticas'),
    # La ruta fija debe preceder al parametro generico para no capturar "ver" como mes.
    path('estadisticas/ver/', ver_estadisticas_view, name='ver_estadisticas_redirect'),
    path('estadisticas/<str:mes>/', ver_estadisticas_view, name='ver_estadisticas'),
    path('estadisticas/<str:mes>/excel/', exportar_estadisticas_excel, name='exportar_estadisticas_excel'),
    path('estadisticas/<str:mes>/pdf/', exportar_estadisticas_pdf, name='exportar_estadisticas_pdf'),
    path('ajax/buscar-clientes/', buscar_clientes_ajax, name='buscar_clientes_ajax'),
    path('ajax/buscar-productos/', buscar_productos_ajax, name='buscar_productos_ajax'),
    path('usuarios/', usuarios_simple, name='usuarios_simple'),





]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Toda la superficie funcional de esta app requiere autenticacion. Los
# permisos especificos se aplican en las vistas sensibles y en la UI.
for _pattern in urlpatterns:
    if hasattr(_pattern, 'callback'):
        _pattern.callback = login_required(_pattern.callback)

_route_permissions = {
    'intervencion_lista': PERM_VER_OPERACIONES,
    'ajax_intervenciones': PERM_VER_OPERACIONES,
    'intervencion_crear': PERM_GESTIONAR_OPERACIONES,
    'intervencion_editar': PERM_GESTIONAR_OPERACIONES,
    'eliminar_intervencion': PERM_GESTIONAR_OPERACIONES,
    'intervencion_detalle': PERM_VER_OPERACIONES,
    'intervencion_excel': PERM_VER_REPORTES,
    'intervencion_pdf': PERM_VER_REPORTES,
    'editar_consumos_intervencion': PERM_GESTIONAR_INVENTARIO,
    'odt_lista': PERM_VER_OPERACIONES,
    'odt_editar': PERM_GESTIONAR_OPERACIONES,
    'odt_detalle': PERM_VER_OPERACIONES,
    'odt_excel': PERM_VER_REPORTES,
    'odt_pdf': PERM_VER_REPORTES,
    'eliminar_odt': PERM_GESTIONAR_OPERACIONES,
    'agregar_item_odt': PERM_GESTIONAR_OPERACIONES,
    'odt_agregar_productos': PERM_GESTIONAR_OPERACIONES,
    'odt_editar_items': PERM_GESTIONAR_OPERACIONES,
    'lista_clientes': PERM_VER_OPERACIONES,
    'agregar_cliente': PERM_GESTIONAR_CATALOGO,
    'modificar_cliente': PERM_GESTIONAR_CATALOGO,
    'eliminar_cliente': PERM_GESTIONAR_CATALOGO,
    'lista_productos': PERM_VER_OPERACIONES,
    'consulta_stock_productos': PERM_VER_OPERACIONES,
    'lista_comprado': PERM_VER_REPORTES,
    'agregar_producto': PERM_GESTIONAR_CATALOGO,
    'modificar_producto': PERM_GESTIONAR_CATALOGO,
    'eliminar_producto': PERM_GESTIONAR_CATALOGO,
    'ingreso_stock_nuevo': PERM_GESTIONAR_INVENTARIO,
    'comprado_editar': PERM_GESTIONAR_INVENTARIO,
    'comprado_eliminar': PERM_GESTIONAR_INVENTARIO,
    'inventario_excel': PERM_VER_REPORTES,
    'inventario_pdf': PERM_VER_REPORTES,
    'lista_categorias': PERM_VER_OPERACIONES,
    'agregar_categoria': PERM_GESTIONAR_CATALOGO,
    'modificar_categoria': PERM_GESTIONAR_CATALOGO,
    'eliminar_categoria': PERM_GESTIONAR_CATALOGO,
    'factorajustecliente_lista': PERM_VER_OPERACIONES,
    'factorajustecliente_crear': PERM_GESTIONAR_CATALOGO,
    'factorajustecliente_editar': PERM_GESTIONAR_CATALOGO,
    'factorajustecliente_eliminar': PERM_GESTIONAR_CATALOGO,
    'alertas': PERM_VER_REPORTES,
    'generar_estadisticas': PERM_VER_REPORTES,
    'ver_estadisticas_redirect': PERM_VER_REPORTES,
    'ver_estadisticas': PERM_VER_REPORTES,
    'buscar_clientes_ajax': PERM_VER_OPERACIONES,
    'buscar_productos_ajax': PERM_VER_OPERACIONES,
}
for _pattern in urlpatterns:
    if hasattr(_pattern, 'callback') and _pattern.name in _route_permissions:
        _pattern.callback = login_required(requiere_permiso(
            _route_permissions[_pattern.name]
        )(_pattern.callback))
