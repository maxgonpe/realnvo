from django.contrib import admin

from . import models as m

MODELOS_ADMIN = [
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
    m.Rendicion,
    m.EntregaFondo,
    m.DetalleRendicion,
    m.AprobacionRendicion,
    m.LiquidacionRendicion,
    m.PagoLiquidacionRendicion,
    m.AplicacionMovimientoBancario,
]

for modelo in MODELOS_ADMIN:
    admin.site.register(modelo)
