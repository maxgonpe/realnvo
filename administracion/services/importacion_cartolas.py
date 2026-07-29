"""
B003 — Importación de cartolas PDF → CartolaBancaria + MovimientoBancario.
B005 — Integrado: análisis de duplicados antes/durante la confirmación.

Montos enteros (sin decimales). Usa clave cifrada del banco (B001) y parser
según plantilla o nombre del banco.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import (
    CartolaBancaria,
    CuentaBancaria,
    ImportacionCartola,
    MovimientoBancario,
    PlantillaMapeoCartola,
)
from .duplicados import (
    ArchivoDuplicadoError,
    calcular_sha256_bytes,
    crear_fingerprint,
    detectar_duplicados_en_lote,
    resumen_deteccion,
)
from .parsers_cartola_pdf import parsear_cartola_pdf


def _leer_bytes(archivo) -> bytes:
    if hasattr(archivo, "seek"):
        archivo.seek(0)
    if hasattr(archivo, "chunks"):
        raw = b"".join(chunk for chunk in archivo.chunks())
    else:
        raw = archivo.read()
    if hasattr(archivo, "seek"):
        archivo.seek(0)
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    return raw


def resolver_plantilla_pdf(cuenta: CuentaBancaria) -> PlantillaMapeoCartola | None:
    qs = PlantillaMapeoCartola.objects.filter(
        banco=cuenta.banco,
        activa=True,
        formato_archivo=PlantillaMapeoCartola.FormatoArchivo.PDF,
    )
    especifica = qs.filter(cuenta_bancaria=cuenta).order_by("-version").first()
    if especifica:
        return especifica
    return qs.filter(cuenta_bancaria__isnull=True).order_by("-version").first()


def _validar_cuenta_para_importar(cuenta: CuentaBancaria) -> None:
    if not cuenta.activa:
        raise ValidationError("La cuenta está inactiva; no acepta importaciones.")
    if not cuenta.banco.activo:
        raise ValidationError("El banco está inactivo.")
    if not cuenta.banco.tiene_clave_cartola:
        raise ValidationError("Configure la clave de cartola del banco (B001).")


def analizar_cartola_pdf(
    *,
    cuenta: CuentaBancaria,
    archivo,
    plantilla: PlantillaMapeoCartola | None = None,
) -> dict:
    """
    B005 — Previsualización: parsea y clasifica duplicados sin guardar movimientos.
    """
    _validar_cuenta_para_importar(cuenta)
    plantilla = plantilla or resolver_plantilla_pdf(cuenta)
    raw = _leer_bytes(archivo)
    sha_hex = calcular_sha256_bytes(raw)
    nombre = Path(getattr(archivo, "name", "cartola.pdf") or "cartola.pdf").name

    data = parsear_cartola_pdf(
        banco=cuenta.banco, archivo=BytesIO(raw), plantilla=plantilla
    )
    det = detectar_duplicados_en_lote(
        cuenta=cuenta, movimientos=data["movimientos"], sha256=sha_hex
    )
    resumen = resumen_deteccion(det)
    resumen.update(
        {
            "nombre_archivo": nombre,
            "sha256": sha_hex,
            "cabecera": {
                "fecha_inicio": data["cabecera"].get("fecha_inicio_periodo"),
                "fecha_fin": data["cabecera"].get("fecha_fin_periodo"),
                "saldo_inicial": data["cabecera"].get("saldo_inicial"),
                "saldo_final": data["cabecera"].get("saldo_final"),
                "titular": data["cabecera"].get("nombre_titular"),
                "parser": data["cabecera"].get("parser"),
            },
            "plantilla": str(plantilla) if plantilla else None,
            "archivo_duplicado": None,
        }
    )
    if det.archivo_duplicado:
        prev = det.archivo_duplicado
        resumen["archivo_duplicado"] = {
            "id": prev.pk,
            "creado_en": prev.creado_en,
            "usuario": (
                prev.creado_por.get_username() if prev.creado_por_id else "—"
            ),
            "estado": prev.get_estado_display(),
            "total_movimientos": prev.total_importadas,
            "nombre_archivo": prev.nombre_archivo,
        }
    return resumen


@transaction.atomic
def importar_cartola_pdf(
    *,
    cuenta: CuentaBancaria,
    archivo,
    usuario,
    plantilla: PlantillaMapeoCartola | None = None,
    omitir_duplicados_exactos: bool = True,
) -> dict:
    _validar_cuenta_para_importar(cuenta)
    plantilla = plantilla or resolver_plantilla_pdf(cuenta)
    raw = _leer_bytes(archivo)
    sha_hex = calcular_sha256_bytes(raw)
    nombre = Path(getattr(archivo, "name", "cartola.pdf") or "cartola.pdf").name

    data = parsear_cartola_pdf(
        banco=cuenta.banco, archivo=BytesIO(raw), plantilla=plantilla
    )
    cab = data["cabecera"]
    movs = data["movimientos"]

    det = detectar_duplicados_en_lote(
        cuenta=cuenta, movimientos=movs, sha256=sha_hex
    )
    if det.archivo_duplicado:
        raise ArchivoDuplicadoError(det.archivo_duplicado)

    importacion = ImportacionCartola(
        cuenta_bancaria=cuenta,
        plantilla=plantilla,
        fecha_desde=cab["fecha_inicio_periodo"],
        fecha_hasta=cab["fecha_fin_periodo"],
        nombre_archivo=nombre,
        sha256=sha_hex,
        estado=ImportacionCartola.Estado.PENDIENTE,
        total_filas=len(movs),
        creado_por=usuario,
        actualizado_por=usuario,
    )
    importacion.archivo.save(nombre, ContentFile(raw), save=False)
    importacion.full_clean()
    importacion.save()

    cartola = CartolaBancaria(
        cuenta_bancaria=cuenta,
        importacion=importacion,
        tipo_documento=cab.get("tipo_documento") or "",
        tipo_cuenta_texto=cab.get("tipo_cuenta_texto") or "",
        numero_cartola=cab.get("numero_cartola") or "",
        fecha_emision=cab.get("fecha_emision"),
        fecha_inicio_periodo=cab["fecha_inicio_periodo"],
        fecha_fin_periodo=cab["fecha_fin_periodo"],
        nombre_titular=cab.get("nombre_titular") or "",
        tratamiento_titular=cab.get("tratamiento_titular") or "",
        correo_electronico=cab.get("correo_electronico") or "",
        numero_cuenta_texto=cab.get("numero_cuenta_texto") or "",
        moneda=cab.get("moneda") or "CLP",
        sucursal_cuenta=cab.get("sucursal_cuenta") or "",
        saldo_inicial=cab.get("saldo_inicial"),
        saldo_final=cab.get("saldo_final"),
        saldo_disponible=cab.get("saldo_disponible"),
        creado_por=usuario,
        actualizado_por=usuario,
    )
    cartola.full_clean()
    cartola.save()

    importados = 0
    duplicados = 0
    posibles = 0
    errores: list[str] = []
    creados: list[MovimientoBancario] = []
    omitidos_archivo = 0

    for fila in det.filas:
        mov = fila.movimiento
        if fila.resultado == "DUPLICADO_EN_ARCHIVO":
            omitidos_archivo += 1
            duplicados += 1
            continue
        if fila.resultado == "DUPLICADO_EXACTO" and omitir_duplicados_exactos:
            duplicados += 1
            continue
        if fila.resultado == "POSIBLE_DUPLICADO":
            posibles += 1
            # MVP: se importa con advertencia (no bloquea)

        try:
            fp = fila.fingerprint or crear_fingerprint(
                cuenta_id=cuenta.pk,
                fecha=mov["fecha_operacion"],
                tipo=mov.get("tipo") or "",
                monto=int(mov.get("monto") or 0),
                numero_documento=mov.get("numero_documento") or "",
                contraparte=mov.get("nombre_contraparte") or "",
                descripcion=mov.get("descripcion_movimiento") or "",
                monto_cargo=int(mov.get("monto_cargo") or 0),
                monto_abono=int(mov.get("monto_abono") or 0),
                saldo_bancario=mov.get("saldo_bancario"),
            )
            obj = MovimientoBancario(
                cuenta_bancaria=cuenta,
                importacion=importacion,
                cartola=cartola,
                fecha_operacion=mov["fecha_operacion"],
                fecha_contable=mov.get("fecha_contable") or mov["fecha_operacion"],
                tipo=mov["tipo"],
                monto=mov["monto"],
                monto_cargo=mov.get("monto_cargo") or 0,
                monto_abono=mov.get("monto_abono") or 0,
                saldo_bancario=mov.get("saldo_bancario"),
                descripcion_original=mov.get("descripcion_original") or "",
                descripcion_movimiento=mov.get("descripcion_movimiento") or "",
                numero_documento=mov.get("numero_documento") or "",
                sucursal_movimiento=mov.get("sucursal_movimiento") or "",
                codigo_sucursal_movimiento=mov.get("codigo_sucursal_movimiento") or "",
                tipo_movimiento=mov.get("tipo_movimiento") or "",
                canal_movimiento=mov.get("canal_movimiento") or "",
                contraparte=mov.get("nombre_contraparte") or "",
                fecha_operacion_original=mov.get("fecha_operacion_original"),
                hora_operacion_original=mov.get("hora_operacion_original") or "",
                numero_fila_origen=mov.get("numero_fila_origen"),
                fingerprint=fp,
                observaciones=(
                    "POSIBLE_DUPLICADO" if fila.resultado == "POSIBLE_DUPLICADO" else ""
                ),
                creado_por=usuario,
                actualizado_por=usuario,
            )
            obj.full_clean()
            obj.save()
            creados.append(obj)
            importados += 1
        except IntegrityError:
            duplicados += 1
            errores.append(
                f"Fila {fila.fila}: IntegrityError (duplicado concurrente omitido)."
            )
        except Exception as exc:  # noqa: BLE001
            errores.append(f"Fila {fila.fila}: {exc}")

    importacion.total_validas = importados
    importacion.total_importadas = importados
    importacion.total_duplicadas = duplicados
    importacion.total_errores = len(errores)
    importacion.total_movimientos = importados
    importacion.estado = (
        ImportacionCartola.Estado.CON_ERRORES
        if errores and not importados
        else ImportacionCartola.Estado.PROCESADA
    )
    importacion.procesada_en = timezone.now()
    importacion.validada_en = timezone.now()
    notas = []
    if posibles:
        notas.append(f"Posibles duplicados importados con advertencia: {posibles}.")
    if omitidos_archivo:
        notas.append(f"Duplicados dentro del archivo omitidos: {omitidos_archivo}.")
    if errores:
        notas.extend(errores[:20])
    importacion.error_importacion = "\n".join(notas)
    importacion.observaciones = (
        f"B005: exactos={det.total_duplicados_exactos}, "
        f"en_archivo={det.total_duplicados_en_archivo}, "
        f"posibles={det.total_posibles}, validos={det.total_validos}"
    )
    importacion.save()

    return {
        "importacion": importacion,
        "cartola": cartola,
        "movimientos": creados,
        "importados": importados,
        "duplicados": duplicados,
        "posibles": posibles,
        "errores": errores,
        "deteccion": resumen_deteccion(det),
    }


def recalcular_fingerprints_cuenta(cuenta: CuentaBancaria | None = None) -> int:
    """Recalcula fingerprints con el algoritmo B005 (útil tras cambiar la fórmula)."""
    qs = MovimientoBancario.objects.all()
    if cuenta:
        qs = qs.filter(cuenta_bancaria=cuenta)
    n = 0
    for mov in qs.iterator():
        fp = crear_fingerprint(
            cuenta_id=mov.cuenta_bancaria_id,
            fecha=mov.fecha_operacion,
            tipo=mov.tipo,
            monto=int(mov.monto or 0),
            referencia=mov.referencia_bancaria or "",
            numero_documento=mov.numero_documento or "",
            contraparte=mov.contraparte or "",
            descripcion=mov.descripcion_movimiento or mov.descripcion_original or "",
            monto_cargo=int(mov.monto_cargo or 0),
            monto_abono=int(mov.monto_abono or 0),
            saldo_bancario=mov.saldo_bancario,
        )
        if mov.fingerprint != fp:
            mov.fingerprint = fp
            mov.save(update_fields=["fingerprint"])
            n += 1
    return n
