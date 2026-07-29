"""Selectores de lectura para rendiciones (R001, R003, R009, R013, R018–R020)."""
from __future__ import annotations

from django.db.models import Count, Q, QuerySet

from ..models import ResponsableRendicion, Rendicion


def listar_responsables(*, q: str = "", solo_activos: bool | None = None) -> QuerySet:
    """R003 — listado filtrable de responsables."""
    qs = ResponsableRendicion.objects.select_related("user").annotate(
        total_rendiciones=Count("rendiciones", distinct=True),
    )
    if solo_activos is True:
        qs = qs.filter(activo=True)
    elif solo_activos is False:
        qs = qs.filter(activo=False)
    q = (q or "").strip()
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q)
            | Q(rut__icontains=q)
            | Q(cargo__icontains=q)
            | Q(area__icontains=q)
            | Q(correo__icontains=q)
            | Q(user__username__icontains=q)
        )
    return qs.order_by("nombre")


def resumen_responsable(responsable: ResponsableRendicion) -> dict:
    """Indicadores básicos para el detalle R003 (se enriquecerán después)."""
    rendiciones = responsable.rendiciones.all()
    return {
        "total": rendiciones.count(),
        "borrador": rendiciones.filter(estado=Rendicion.Estado.BORRADOR).count(),
        "pendientes": rendiciones.exclude(
            estado__in=[
                Rendicion.Estado.BORRADOR,
                Rendicion.Estado.CERRADA,
                Rendicion.Estado.LIQUIDADA,
                Rendicion.Estado.RECHAZADA,
                Rendicion.Estado.ANULADA,
            ]
        ).count(),
        "ultima": rendiciones.order_by("-creado_en").first(),
    }


# TODO(R001): def listar_rendiciones(filtros) -> QuerySet: ...
# TODO(R009): def totales_rendicion(rendicion_id) -> dict: ...
# TODO(R013): def historial_aprobaciones(rendicion_id) -> QuerySet: ...
# TODO(R020): def dashboard_rendiciones(...) -> dict: ...
