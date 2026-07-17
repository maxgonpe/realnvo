from django.contrib import admin

from . import models as m


class DetalleRendicionInline(admin.TabularInline):
    model = m.DetalleRendicion
    extra = 0
    fields = (
        "fecha",
        "tipo_documento",
        "numero_documento",
        "proveedor",
        "descripcion",
        "total",
        "comprobante",
        "estado_revision",
    )
    readonly_fields = ()
    show_change_link = True


@admin.register(m.DetalleRendicion)
class DetalleRendicionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "rendicion",
        "fecha",
        "tipo_documento",
        "numero_documento",
        "proveedor",
        "descripcion_corta",
        "total",
        "tiene_imagen",
        "estado_revision",
    )
    list_filter = ("tipo_documento", "estado_revision", "forma_pago", "fecha")
    search_fields = (
        "proveedor",
        "numero_documento",
        "descripcion",
        "rut_proveedor",
        "rendicion__numero",
    )
    list_select_related = ("rendicion",)
    date_hierarchy = "fecha"
    ordering = ("-fecha", "-id")
    readonly_fields = ("creado_en", "actualizado_en")

    fieldsets = (
        (
            "Rendición",
            {"fields": ("rendicion",)},
        ),
        (
            "Documento",
            {
                "fields": (
                    "fecha",
                    "tipo_documento",
                    "numero_documento",
                    "proveedor",
                    "rut_proveedor",
                    "sucursal",
                    "descripcion",
                    "forma_pago",
                )
            },
        ),
        (
            "Montos",
            {"fields": ("neto", "iva", "total", "monto_aprobado")},
        ),
        (
            "Comprobante y revisión",
            {
                "fields": (
                    "comprobante",
                    "estado_revision",
                    "motivo_observacion",
                    "justificacion_sin_documento",
                    "categoria",
                    "subcategoria",
                )
            },
        ),
        (
            "Auditoría",
            {
                "classes": ("collapse",),
                "fields": (
                    "creado_en",
                    "actualizado_en",
                    "creado_por",
                    "actualizado_por",
                ),
            },
        ),
    )

    @admin.display(description="Descripción")
    def descripcion_corta(self, obj):
        texto = obj.descripcion or ""
        return texto[:50] + ("…" if len(texto) > 50 else "")

    @admin.display(description="Imagen", boolean=True)
    def tiene_imagen(self, obj):
        return bool(obj.comprobante)


@admin.register(m.Rendicion)
class RendicionAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "responsable",
        "estado",
        "periodo_desde",
        "periodo_hasta",
        "motivo",
        "fecha_presentacion",
    )
    list_filter = ("estado",)
    search_fields = ("numero", "motivo", "responsable__nombre")
    list_select_related = ("responsable",)
    inlines = [DetalleRendicionInline]
    ordering = ("-creado_en", "-id")


MODELOS_SIMPLE = [
    m.Banco,
    m.CuentaBancaria,
    m.ImportacionCartola,
    m.MovimientoBancario,
    m.ConciliacionBancaria,
    m.ExclusionMovimientoBancario,
    m.FacturaVenta,
    m.GestionCobranza,
    m.EmpresaFactoring,
    m.OperacionFactoring,
    m.EventoFactoring,
    m.FlujoFactoring,
    m.PagoCliente,
    m.AplicacionPagoFactura,
    m.DevolucionPagoCliente,
    m.AlertaCobranza,
    m.ResponsableRendicion,
    m.CategoriaGasto,
    m.SubcategoriaGasto,
    m.EntregaFondo,
    m.AprobacionRendicion,
    m.LiquidacionRendicion,
    m.PagoLiquidacionRendicion,
    m.AplicacionMovimientoBancario,
]

for modelo in MODELOS_SIMPLE:
    admin.site.register(modelo)
