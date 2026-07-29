"""
F001–F014 — Vistas de facturación y cobranza (esqueleto).
"""
from django.contrib.auth.decorators import login_required

from ._esqueleto import render_esqueleto


@login_required
def factura_lista(request):
    """F003 — Lista de facturas."""
    return render_esqueleto(
        request,
        "F003",
        "Lista de facturas",
        "administracion/facturacion/factura_lista.html",
    )


@login_required
def factura_crear(request):
    """F002 — Registro de facturas."""
    return render_esqueleto(
        request,
        "F002",
        "Registro / importación de facturas",
        "administracion/facturacion/factura_form.html",
    )


@login_required
def pago_crear(request):
    """F005 — Registro de pagos."""
    return render_esqueleto(
        request,
        "F005",
        "Registro de pagos de clientes",
        "administracion/facturacion/pago_form.html",
    )


@login_required
def cobranza_lista(request):
    """F010 — Gestión de cobranza."""
    return render_esqueleto(
        request,
        "F010",
        "Gestión de cobranza",
        "administracion/facturacion/cobranza_lista.html",
    )


@login_required
def antiguedad_saldos(request):
    """F012 — Antigüedad de saldos."""
    return render_esqueleto(
        request,
        "F012",
        "Antigüedad de saldos",
        "administracion/facturacion/antiguedad_saldos.html",
    )
