"""
R010–R022 — Vistas adicionales de rendiciones aún no implementadas.

Las vistas activas (lista, crear, escritorio, OCR, PDF) están en
``views.rendiciones``.
"""
from django.contrib.auth.decorators import login_required

from ._esqueleto import render_esqueleto


@login_required
def entrega_fondo_crear(request, pk):
    """R005 — Entregas de fondo."""
    return render_esqueleto(
        request,
        "R005",
        f"Entrega de fondo — rendición #{pk}",
        "administracion/rendiciones/entrega_fondo_form.html",
        objeto_id=pk,
    )


@login_required
def rendicion_presentar(request, pk):
    """R010 — Presentación formal."""
    return render_esqueleto(
        request,
        "R010",
        f"Presentar rendición #{pk}",
        "administracion/rendiciones/presentar.html",
        objeto_id=pk,
    )


@login_required
def rendicion_revisar(request, pk):
    """R011 — Revisión y observaciones."""
    return render_esqueleto(
        request,
        "R011",
        f"Revisar rendición #{pk}",
        "administracion/rendiciones/revisar.html",
        objeto_id=pk,
    )


@login_required
def rendicion_aprobar(request, pk):
    """R012 — Aprobación / rechazo."""
    return render_esqueleto(
        request,
        "R012",
        f"Aprobar / rechazar rendición #{pk}",
        "administracion/rendiciones/aprobar.html",
        objeto_id=pk,
    )


@login_required
def rendicion_liquidar(request, pk):
    """R014 — Liquidación."""
    return render_esqueleto(
        request,
        "R014",
        f"Liquidar rendición #{pk}",
        "administracion/rendiciones/liquidar.html",
        objeto_id=pk,
    )


@login_required
def rendicion_dashboard(request):
    """R020 — Dashboard de rendiciones."""
    return render_esqueleto(
        request,
        "R020",
        "Dashboard de rendiciones",
        "administracion/rendiciones/dashboard.html",
    )


@login_required
def rendicion_export_excel(request, pk):
    """R019 — Exportación Excel."""
    return render_esqueleto(
        request,
        "R019",
        f"Exportación Excel — rendición #{pk}",
        "administracion/rendiciones/export_excel.html",
        objeto_id=pk,
    )
