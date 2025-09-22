from django.urls import path
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
                   lista_productos, agregar_item_odt, agregar_categoria,\
                   modificar_categoria,eliminar_categoria,lista_categorias,\
                   IntervencionAjaxListView, factorajustecliente_lista,\
                   factorajustecliente_crear, factorajustecliente_editar,\
                   factorajustecliente_eliminar,odt_agregar_productos,\
                   odt_editar_items, ingreso_stock_nuevo, exportar_inventario_pdf,\
                   exportar_inventario_excel, generar_estadisticas_view,\
                   generar_estadisticas_mensuales, ver_estadisticas_view,\
                   alertas_view, editar_consumos_intervencion 

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
    path('estadisticas/<str:mes>/', ver_estadisticas_view, name='ver_estadisticas'),  # Ajusta esto
    path('estadisticas/ver/', ver_estadisticas_view, name='ver_estadisticas_redirect'),  # Agrega esta línea
    




]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)