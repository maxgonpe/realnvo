"""
X001–X013 — Vistas de factoring (esqueleto).
"""
from django.contrib.auth.decorators import login_required

from ._esqueleto import render_esqueleto


@login_required
def empresa_factoring_lista(request):
    """X001 — Empresas de factoring."""
    return render_esqueleto(
        request,
        "X001",
        "Empresas de factoring",
        "administracion/factoring/empresa_lista.html",
    )


@login_required
def operacion_lista(request):
    """X002 — Operaciones de factoring."""
    return render_esqueleto(
        request,
        "X002",
        "Operaciones de factoring",
        "administracion/factoring/operacion_lista.html",
    )


@login_required
def operacion_detalle(request, pk):
    """X002/X003 — Detalle y eventos."""
    return render_esqueleto(
        request,
        "X003",
        f"Operación de factoring #{pk}",
        "administracion/factoring/operacion_detalle.html",
        objeto_id=pk,
    )


@login_required
def factoring_reportes(request):
    """X012 — Reportes de factoring."""
    return render_esqueleto(
        request,
        "X012",
        "Reportes de factoring",
        "administracion/factoring/reportes.html",
    )
