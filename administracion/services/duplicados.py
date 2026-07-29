"""
B005 — Detección de duplicados de cartolas y movimientos bancarios.

Niveles:
1. ARCHIVO_DUPLICADO — misma cuenta + SHA-256
2. DUPLICADO_EXACTO — mismo fingerprint (BD o dentro del archivo)
3. POSIBLE_DUPLICADO — misma fecha/tipo/monto/contraparte, distinta huella
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable

from django.db.models import QuerySet

from ..models import CuentaBancaria, ImportacionCartola, MovimientoBancario


# ---------------------------------------------------------------------------
# Normalización
# ---------------------------------------------------------------------------


def normalizar_texto(valor: str | None) -> str:
    texto = (valor or "").strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto.casefold()


def normalizar_rut(rut: str | None) -> str:
    if not rut:
        return ""
    return (
        rut.strip()
        .upper()
        .replace(".", "")
        .replace(" ", "")
        .replace("-", "")
    )


def normalizar_cuenta(numero: str | None) -> str:
    if not numero:
        return ""
    return re.sub(r"[\s.\-_/]", "", (numero or "").strip().upper())


def calcular_sha256_bytes(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def crear_fingerprint(
    *,
    cuenta_id: int,
    fecha: date,
    tipo: str,
    monto: int,
    referencia: str = "",
    numero_documento: str = "",
    contraparte: str = "",
    descripcion: str = "",
    monto_cargo: int = 0,
    monto_abono: int = 0,
    saldo_bancario=None,
) -> str:
    """
    Huella estable del movimiento (montos enteros, sin decimales).
    Incluye cargo/abono/saldo para distinguir filas casi idénticas de la cartola.
    """
    partes = [
        str(cuenta_id),
        fecha.isoformat() if fecha else "",
        (tipo or "").strip().upper(),
        str(int(monto or 0)),
        str(int(monto_cargo or 0)),
        str(int(monto_abono or 0)),
        "" if saldo_bancario is None else str(int(saldo_bancario)),
        normalizar_texto(referencia),
        normalizar_texto(numero_documento),
        normalizar_texto(contraparte),
        normalizar_texto(descripcion),
    ]
    base = "|".join(partes)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def fingerprint_desde_dict(cuenta_id: int, mov: dict) -> str:
    return crear_fingerprint(
        cuenta_id=cuenta_id,
        fecha=mov["fecha_operacion"],
        tipo=mov.get("tipo") or "",
        monto=int(mov.get("monto") or 0),
        referencia=mov.get("referencia_bancaria") or "",
        numero_documento=mov.get("numero_documento") or "",
        contraparte=mov.get("nombre_contraparte") or mov.get("contraparte") or "",
        descripcion=mov.get("descripcion_movimiento") or mov.get("descripcion_original") or "",
        monto_cargo=int(mov.get("monto_cargo") or 0),
        monto_abono=int(mov.get("monto_abono") or 0),
        saldo_bancario=mov.get("saldo_bancario"),
    )


def clave_posible_duplicado(mov: dict) -> tuple:
    return (
        mov.get("fecha_operacion"),
        (mov.get("tipo") or "").upper(),
        int(mov.get("monto") or 0),
        normalizar_texto(mov.get("nombre_contraparte") or mov.get("contraparte") or ""),
    )


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


def buscar_archivo_duplicado(
    *, cuenta: CuentaBancaria, sha256: str
) -> ImportacionCartola | None:
    return (
        ImportacionCartola.objects.filter(cuenta_bancaria=cuenta, sha256=sha256)
        .exclude(estado=ImportacionCartola.Estado.ANULADA)
        .select_related("cuenta_bancaria", "creado_por")
        .order_by("-creado_en")
        .first()
    )


def buscar_movimiento_duplicado(
    *, cuenta: CuentaBancaria, fingerprint: str
) -> MovimientoBancario | None:
    return (
        MovimientoBancario.objects.filter(
            cuenta_bancaria=cuenta, fingerprint=fingerprint
        )
        .select_related("importacion")
        .first()
    )


def fingerprints_existentes(
    *, cuenta: CuentaBancaria, fingerprints: Iterable[str]
) -> set[str]:
    fps = [f for f in fingerprints if f]
    if not fps:
        return set()
    return set(
        MovimientoBancario.objects.filter(
            cuenta_bancaria=cuenta, fingerprint__in=fps
        ).values_list("fingerprint", flat=True)
    )


def mapa_posibles_existentes(
    *, cuenta: CuentaBancaria, claves: Iterable[tuple]
) -> dict[tuple, list[int]]:
    """
    Para posibles duplicados: indexa movimientos existentes por
    (fecha, tipo, monto, contraparte_norm) → lista de pks.
    """
    fechas = {c[0] for c in claves if c and c[0]}
    if not fechas:
        return {}
    qs: QuerySet = MovimientoBancario.objects.filter(
        cuenta_bancaria=cuenta, fecha_operacion__in=fechas
    ).only(
        "id",
        "fecha_operacion",
        "tipo",
        "monto",
        "contraparte",
        "fingerprint",
    )
    indice: dict[tuple, list[int]] = {}
    for m in qs:
        clave = (
            m.fecha_operacion,
            (m.tipo or "").upper(),
            int(m.monto or 0),
            normalizar_texto(m.contraparte),
        )
        indice.setdefault(clave, []).append(m.pk)
    return indice


# ---------------------------------------------------------------------------
# Clasificación en lote
# ---------------------------------------------------------------------------


@dataclass
class ResultadoFilaDuplicado:
    fila: int
    movimiento: dict
    fingerprint: str
    resultado: str  # VALIDO | DUPLICADO_EXACTO | DUPLICADO_EN_ARCHIVO | POSIBLE_DUPLICADO
    movimiento_existente_id: int | None = None
    mensaje: str = ""


@dataclass
class ResultadoDeteccion:
    archivo_duplicado: ImportacionCartola | None = None
    filas: list[ResultadoFilaDuplicado] = field(default_factory=list)
    total_validos: int = 0
    total_duplicados_exactos: int = 0
    total_duplicados_en_archivo: int = 0
    total_posibles: int = 0

    @property
    def bloquea_importacion(self) -> bool:
        return self.archivo_duplicado is not None


def detectar_duplicados_en_lote(
    *,
    cuenta: CuentaBancaria,
    movimientos: list[dict],
    sha256: str | None = None,
) -> ResultadoDeteccion:
    """
    Clasifica cada fila sin N+1:
    recolecta fingerprints → consulta __in → clasifica en memoria.
    """
    resultado = ResultadoDeteccion()
    if sha256:
        resultado.archivo_duplicado = buscar_archivo_duplicado(
            cuenta=cuenta, sha256=sha256
        )
        if resultado.archivo_duplicado:
            return resultado

    preparados: list[tuple[int, dict, str]] = []
    fingerprints_archivo: set[str] = set()
    for idx, mov in enumerate(movimientos, start=1):
        fp = fingerprint_desde_dict(cuenta.pk, mov)
        preparados.append((idx, mov, fp))

    existentes_map = {
        fp: pk
        for fp, pk in MovimientoBancario.objects.filter(
            cuenta_bancaria=cuenta, fingerprint__in=[fp for _, _, fp in preparados]
        ).values_list("fingerprint", "id")
    }
    existentes = set(existentes_map)
    claves_posibles = [clave_posible_duplicado(m) for _, m, _ in preparados]
    indice_posibles = mapa_posibles_existentes(cuenta=cuenta, claves=claves_posibles)

    for fila, mov, fp in preparados:
        if fp in fingerprints_archivo:
            resultado.filas.append(
                ResultadoFilaDuplicado(
                    fila=fila,
                    movimiento=mov,
                    fingerprint=fp,
                    resultado="DUPLICADO_EN_ARCHIVO",
                    mensaje="MOVIMIENTO_DUPLICADO_EN_ARCHIVO",
                )
            )
            resultado.total_duplicados_en_archivo += 1
            continue

        fingerprints_archivo.add(fp)

        if fp in existentes:
            resultado.filas.append(
                ResultadoFilaDuplicado(
                    fila=fila,
                    movimiento=mov,
                    fingerprint=fp,
                    resultado="DUPLICADO_EXACTO",
                    movimiento_existente_id=existentes_map.get(fp),
                    mensaje="Coincide fingerprint con movimiento ya registrado.",
                )
            )
            resultado.total_duplicados_exactos += 1
            continue

        clave = clave_posible_duplicado(mov)
        posibles_ids = indice_posibles.get(clave, [])
        if posibles_ids:
            resultado.filas.append(
                ResultadoFilaDuplicado(
                    fila=fila,
                    movimiento=mov,
                    fingerprint=fp,
                    resultado="POSIBLE_DUPLICADO",
                    movimiento_existente_id=posibles_ids[0],
                    mensaje=(
                        "Misma fecha, tipo, monto y contraparte que un movimiento "
                        "existente; se importará con advertencia."
                    ),
                )
            )
            resultado.total_posibles += 1
            continue

        resultado.filas.append(
            ResultadoFilaDuplicado(
                fila=fila,
                movimiento=mov,
                fingerprint=fp,
                resultado="VALIDO",
                mensaje="Listo para importar.",
            )
        )
        resultado.total_validos += 1

    return resultado


class ArchivoDuplicadoError(Exception):
    """Señala ARCHIVO_DUPLICADO con contexto para la UI."""

    codigo = "ARCHIVO_DUPLICADO"

    def __init__(self, importacion: ImportacionCartola):
        self.importacion = importacion
        super().__init__(
            f"ARCHIVO_DUPLICADO: esta cartola ya fue importada "
            f"el {importacion.creado_en} "
            f"({importacion.total_importadas} movimientos, "
            f"estado {importacion.get_estado_display()})."
        )


def resumen_deteccion(det: ResultadoDeteccion) -> dict[str, Any]:
    return {
        "archivo_duplicado_id": (
            det.archivo_duplicado.pk if det.archivo_duplicado else None
        ),
        "total_filas": len(det.filas),
        "total_validos": det.total_validos,
        "total_duplicados_exactos": det.total_duplicados_exactos,
        "total_duplicados_en_archivo": det.total_duplicados_en_archivo,
        "total_posibles": det.total_posibles,
        "filas": [
            {
                "fila": f.fila,
                "fecha": f.movimiento.get("fecha_operacion"),
                "tipo": f.movimiento.get("tipo"),
                "monto": f.movimiento.get("monto"),
                "descripcion": (
                    f.movimiento.get("descripcion_movimiento")
                    or f.movimiento.get("descripcion_original")
                    or ""
                )[:80],
                "resultado": f.resultado,
                "mensaje": f.mensaje,
                "movimiento_existente_id": f.movimiento_existente_id,
            }
            for f in det.filas
        ],
    }
