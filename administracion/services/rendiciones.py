"""R003 — Servicios de dominio para responsables de rendición."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import ResponsableRendicion


def normalizar_rut(rut: str) -> str:
    """Quita puntos/espacios y deja el dígito verificador en mayúscula."""
    if not rut:
        return ""
    limpio = (
        rut.strip()
        .upper()
        .replace(".", "")
        .replace(" ", "")
    )
    return limpio


def _validar_rut_activo_unico(rut: str, exclude_pk: int | None = None) -> None:
    if not rut:
        return
    qs = ResponsableRendicion.objects.filter(activo=True, rut=rut)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise ValidationError(
            {"rut": "Ya existe un responsable activo con este RUT."}
        )


@transaction.atomic
def crear_responsable(*, datos: dict, usuario) -> ResponsableRendicion:
    datos = dict(datos)
    datos["rut"] = normalizar_rut(datos.get("rut") or "")
    _validar_rut_activo_unico(datos["rut"])
    if datos.get("activo", True) is False:
        # Alta inactiva permitida, pero sin chocar RUT activo.
        pass
    responsable = ResponsableRendicion(
        user=datos.get("user"),
        nombre=(datos.get("nombre") or "").strip(),
        rut=datos["rut"],
        cargo=(datos.get("cargo") or "").strip(),
        area=(datos.get("area") or "").strip(),
        correo=(datos.get("correo") or "").strip(),
        telefono=(datos.get("telefono") or "").strip(),
        activo=bool(datos.get("activo", True)),
        observaciones=(datos.get("observaciones") or "").strip(),
        creado_por=usuario,
        actualizado_por=usuario,
    )
    if not responsable.nombre:
        raise ValidationError({"nombre": "El nombre es obligatorio."})
    responsable.full_clean()
    responsable.save()
    return responsable


@transaction.atomic
def actualizar_responsable(
    *, responsable: ResponsableRendicion, datos: dict, usuario
) -> ResponsableRendicion:
    datos = dict(datos)
    datos["rut"] = normalizar_rut(datos.get("rut") or "")
    activo = bool(datos.get("activo", responsable.activo))
    if activo:
        _validar_rut_activo_unico(datos["rut"], exclude_pk=responsable.pk)

    responsable.user = datos.get("user")
    responsable.nombre = (datos.get("nombre") or "").strip()
    responsable.rut = datos["rut"]
    responsable.cargo = (datos.get("cargo") or "").strip()
    responsable.area = (datos.get("area") or "").strip()
    responsable.correo = (datos.get("correo") or "").strip()
    responsable.telefono = (datos.get("telefono") or "").strip()
    responsable.activo = activo
    responsable.observaciones = (datos.get("observaciones") or "").strip()
    responsable.actualizado_por = usuario

    if not responsable.nombre:
        raise ValidationError({"nombre": "El nombre es obligatorio."})
    responsable.full_clean()
    responsable.save()
    return responsable


@transaction.atomic
def activar_responsable(*, responsable: ResponsableRendicion, usuario) -> ResponsableRendicion:
    rut = normalizar_rut(responsable.rut)
    _validar_rut_activo_unico(rut, exclude_pk=responsable.pk)
    responsable.rut = rut
    responsable.activo = True
    responsable.actualizado_por = usuario
    responsable.save(update_fields=["rut", "activo", "actualizado_por", "actualizado_en"])
    return responsable


@transaction.atomic
def desactivar_responsable(
    *, responsable: ResponsableRendicion, usuario
) -> ResponsableRendicion:
    """Desactivar no elimina rendiciones ni el historial."""
    responsable.activo = False
    responsable.actualizado_por = usuario
    responsable.save(update_fields=["activo", "actualizado_por", "actualizado_en"])
    return responsable
