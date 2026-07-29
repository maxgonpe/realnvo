"""
B008 — Clasificación manual de movimientos bancarios.

Asigna categoría administrativa sin alterar el dato bancario original
ni crear aplicaciones / conciliación.
"""
from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import ClasificacionMovimientoBancario, MovimientoBancario
from ..permissions import (
    PERM_BANCO_CLASIFICAR,
    PERM_BANCO_RECLASIFICAR_CONCILIADO,
    usuario_tiene_permiso,
)


def _normalizar_texto(valor: str | None) -> str:
    return (valor or "").strip()


def _normalizar_rut(valor: str | None) -> str:
    rut = (valor or "").strip().upper().replace(".", "").replace(" ", "")
    return rut


@transaction.atomic
def clasificar_movimiento(
    *,
    movimiento_id: int,
    categoria: str,
    contraparte_normalizada: str = "",
    rut_contraparte_normalizado: str = "",
    observacion: str = "",
    usuario,
) -> ClasificacionMovimientoBancario:
    """
    Crea una clasificación activa. Si ya existe una activa, la desactiva
    (historial) y deja la nueva como única activa.
    """
    if not usuario_tiene_permiso(usuario, PERM_BANCO_CLASIFICAR):
        raise PermissionDenied("Sin permiso para clasificar movimientos.")

    movimiento = (
        MovimientoBancario.objects.select_for_update()
        .select_related("cuenta_bancaria")
        .get(pk=movimiento_id)
    )

    categoria = (categoria or "").strip()
    contraparte = _normalizar_texto(contraparte_normalizada)
    rut = _normalizar_rut(rut_contraparte_normalizado)
    observacion = _normalizar_texto(observacion)

    validas = {
        c for c, _ in ClasificacionMovimientoBancario.categorias_para_tipo(
            movimiento.tipo
        )
    }
    if categoria not in validas:
        raise ValidationError(
            {
                "categoria": (
                    f"La categoría no es compatible con un movimiento "
                    f"{movimiento.get_tipo_display()}."
                )
            }
        )

    if (
        categoria in ClasificacionMovimientoBancario.CATEGORIAS_OTRO
        and not observacion
    ):
        raise ValidationError(
            {"observacion": "Las categorías «OTRO» requieren observación."}
        )

    anterior = (
        ClasificacionMovimientoBancario.objects.select_for_update()
        .filter(movimiento=movimiento, activa=True)
        .first()
    )

    es_reclasificacion = anterior is not None
    conciliado = (
        movimiento.estado_conciliacion
        == MovimientoBancario.EstadoConciliacion.CONCILIADO
    )

    if es_reclasificacion and conciliado:
        if not usuario_tiene_permiso(
            usuario, PERM_BANCO_RECLASIFICAR_CONCILIADO
        ):
            raise PermissionDenied(
                "Un movimiento conciliado solo puede reclasificarse "
                "con permiso especial."
            )
        if not observacion:
            raise ValidationError(
                {
                    "observacion": (
                        "La observación es obligatoria al reclasificar "
                        "un movimiento conciliado."
                    )
                }
            )

    if anterior:
        anterior.activa = False
        anterior.actualizado_por = usuario
        anterior.save(
            update_fields=["activa", "actualizado_por", "actualizado_en"]
        )

    nueva = ClasificacionMovimientoBancario(
        movimiento=movimiento,
        categoria=categoria,
        contraparte_normalizada=contraparte,
        rut_contraparte_normalizado=rut,
        observacion=observacion,
        activa=True,
        origen=ClasificacionMovimientoBancario.Origen.MANUAL,
        clasificado_por=usuario,
        clasificado_en=timezone.now(),
        clasificacion_anterior=anterior,
        creado_por=usuario,
        actualizado_por=usuario,
    )
    nueva.full_clean()
    nueva.save()

    # La clasificación no cambia el estado de conciliación ni crea aplicaciones.
    return nueva


def historial_clasificaciones(movimiento_id: int):
    return (
        ClasificacionMovimientoBancario.objects.filter(
            movimiento_id=movimiento_id
        )
        .select_related("clasificado_por", "clasificacion_anterior")
        .order_by("-clasificado_en", "-id")
    )
