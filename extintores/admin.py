from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from .models import Cliente, Intervencion, DetalleIntervencion,\
                    Odt, DetalleOdt, Producto, ItemOdt,\
                    TechnicianProfile,CompatibilidadProducto,\
                    CategoriaProducto,ImagenIntervencion,\
                    Bitacora, FactorAjusteCliente, IngresoStock,\
                    DetalleIngreso, EstadisticaMensual, EstadisticaDetalleExtintor,\
                    EstadisticaDetalleProducto, HistorialServicio,ItemIntervencion 

User = get_user_model()

class DetalleInline(admin.TabularInline):
    model = DetalleIntervencion
    extra = 1

@admin.register(Intervencion)
class IntervencionAdmin(admin.ModelAdmin):
    list_display = ['id', 'cliente', 'tipo', 'fecha']
    inlines = [DetalleInline]

class ProductoAdmin(admin.ModelAdmin):
    list_display = ['id', 'categoria','nombre','precio_unitario']

@admin.register(TechnicianProfile)
class TechnicianProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'signature','user_full_name', 'specialization', 'professional_id')
    search_fields = ('user__first_name', 'user__last_name')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = "Técnico"

@admin.register(CompatibilidadProducto)
class CompatibilidadProductoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'detalle_odt', 'motivo')
    search_fields = ('producto__nombre', 'detalle_odt__pk')

class BitacoraAdmin(admin.ModelAdmin):
    list_display = ['id', 'usuario','accion','modelo','objeto_id','descripcion','fecha']

class DetalleIntervencionAdmin(admin.ModelAdmin):
    list_display = ['id','estado', 'intervencion','agente','peso','extintor_abollado','habilitado_un_ano']

class ItemOdtAdmin(admin.ModelAdmin):
    list_display = ['id', 'odt','producto','precio_unitario','cantidad']

class EstadisticaMensualAdmin(admin.ModelAdmin):
    list_display = ['id', 'mes','tipo','cantidad_intervenciones','cantidad_extintores','tipo_intervencion','cantidad_odt','total_productos_utilizados','categoria_producto']

class EstadisticaDetalleExtintorAdmin(admin.ModelAdmin):
    list_display = ['id', 'mes','tipo_intervencion','agente','peso','cantidad','cliente','estado']

class EstadisticaDetalleProductoAdmin(admin.ModelAdmin):
    list_display = ['id', 'mes','producto','cantidad','subtotal','cliente','nombre']

class ItemIntervencionAdmin(admin.ModelAdmin):
    list_display = ['id', 'intervencion','producto','cantidad']

admin.site.register(Cliente)
#admin.site.register(Intervencion)
admin.site.register(DetalleIntervencion,DetalleIntervencionAdmin)
admin.site.register(Odt)
admin.site.register(DetalleOdt)
admin.site.register(Producto,ProductoAdmin)
admin.site.register(ItemOdt,ItemOdtAdmin)
admin.site.register(CategoriaProducto)
admin.site.register(ImagenIntervencion)
admin.site.register(Bitacora,BitacoraAdmin)
admin.site.register(FactorAjusteCliente)
admin.site.register(DetalleIngreso)
admin.site.register(IngresoStock)
admin.site.register(EstadisticaMensual, EstadisticaMensualAdmin )
admin.site.register(EstadisticaDetalleExtintor, EstadisticaDetalleExtintorAdmin)
admin.site.register(EstadisticaDetalleProducto, EstadisticaDetalleProductoAdmin)
admin.site.register(HistorialServicio)
admin.site.register(ItemIntervencion,ItemIntervencionAdmin)