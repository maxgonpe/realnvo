"""Selectores de lectura para banco y conciliación (B001–B002, B004, …)."""
from __future__ import annotations

from django.db.models import Count, Prefetch, Q, QuerySet

from ..models import Banco, CampoMapeoCartola, CuentaBancaria, PlantillaMapeoCartola


def listar_bancos(
    *, q: str = "", solo_activos: bool | None = None
) -> QuerySet:
    """B001 — listado filtrable de bancos."""
    qs = Banco.objects.annotate(
        total_cuentas=Count("cuentas"),
        total_cuentas_activas=Count("cuentas", filter=Q(cuentas__activa=True)),
        total_plantillas=Count("plantillas_cartola"),
    ).order_by("nombre")
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))
    if solo_activos is True:
        qs = qs.filter(activo=True)
    elif solo_activos is False:
        qs = qs.filter(activo=False)
    return qs


def resumen_banco(banco: Banco) -> dict:
    return {
        "total_cuentas": banco.cuentas.count(),
        "cuentas_activas": banco.cuentas.filter(activa=True).count(),
        "plantillas": banco.plantillas_cartola.count(),
        "plantillas_activas": banco.plantillas_cartola.filter(activa=True).count(),
        "tiene_clave_cartola": banco.tiene_clave_cartola,
        "clave_actualizada_en": banco.clave_cartola_actualizada_en,
    }


def listar_cuentas(
    *,
    q: str = "",
    solo_activas: bool | None = None,
    banco_id: int | None = None,
) -> QuerySet:
    """B002 — listado filtrable de cuentas."""
    qs = (
        CuentaBancaria.objects.select_related("banco")
        .annotate(
            total_importaciones=Count("importaciones"),
            total_movimientos=Count("movimientos"),
        )
        .order_by("banco__nombre", "nombre")
    )
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q)
            | Q(numero_cuenta__icontains=q)
            | Q(titular__icontains=q)
            | Q(banco__nombre__icontains=q)
        )
    if solo_activas is True:
        qs = qs.filter(activa=True)
    elif solo_activas is False:
        qs = qs.filter(activa=False)
    if banco_id:
        qs = qs.filter(banco_id=banco_id)
    return qs


def resumen_cuenta(cuenta: CuentaBancaria) -> dict:
    ultima = cuenta.importaciones.order_by("-creado_en").first()
    return {
        "total_importaciones": cuenta.importaciones.count(),
        "total_movimientos": cuenta.movimientos.count(),
        "ultima_cartola": ultima,
    }


def listar_plantillas_mapeo(
    *,
    q: str = "",
    solo_activas: bool | None = None,
    banco_id: int | None = None,
) -> QuerySet:
    """B004 — listado filtrable de plantillas."""
    qs = (
        PlantillaMapeoCartola.objects.select_related("banco", "cuenta_bancaria")
        .annotate(total_campos=Count("campos"))
        .order_by("banco__nombre", "nombre", "-version")
    )
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q)
            | Q(banco__nombre__icontains=q)
            | Q(cuenta_bancaria__numero_cuenta__icontains=q)
            | Q(observaciones__icontains=q)
        )
    if solo_activas is True:
        qs = qs.filter(activa=True)
    elif solo_activas is False:
        qs = qs.filter(activa=False)
    if banco_id:
        qs = qs.filter(banco_id=banco_id)
    return qs


def plantilla_con_campos(pk: int) -> PlantillaMapeoCartola:
    return (
        PlantillaMapeoCartola.objects.select_related("banco", "cuenta_bancaria")
        .prefetch_related(
            Prefetch(
                "campos",
                queryset=CampoMapeoCartola.objects.order_by("orden", "id"),
            )
        )
        .get(pk=pk)
    )


def resumen_plantilla(plantilla: PlantillaMapeoCartola) -> dict:
    from ..services.bancos import validar_plantilla

    try:
        validacion = validar_plantilla(plantilla=plantilla)
        valida = True
        esquema = validacion["esquema"]
        error = ""
    except Exception as exc:  # noqa: BLE001 — resumen UI
        valida = False
        esquema = None
        error = str(exc)

    return {
        "total_campos": plantilla.campos.count(),
        "valida": valida,
        "esquema": esquema,
        "error_validacion": error,
        "importaciones": plantilla.importaciones.count(),
        "importaciones_procesadas": plantilla.importaciones.filter(
            estado="PROCESADA"
        ).count(),
    }
