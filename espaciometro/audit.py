from __future__ import annotations

from django.db.models import QuerySet

from .models import (
    CandidatoMantenimiento,
    LiberacionMantenimiento,
    LoteCandidatosMantenimiento,
    RegistroDescargaRespaldo,
    RespaldoMantenimiento,
    RetiroRespaldoServidor,
    bytes_legibles,
)


# =============================================================================
# ESP016 — AUDITORÍA
# =============================================================================
#
# Este módulo NO:
#
# - elimina archivos;
# - modifica respaldos;
# - modifica lotes;
# - genera nuevas mediciones;
# - realiza escaneos del filesystem;
#
# Solamente reconstruye la evidencia que ya existe
# en la base de datos de Espaciómetro.
# =============================================================================


def _evento(
    *,
    fecha,
    etapa,
    codigo,
    titulo,
    estado="",
    usuario="",
    detalle="",
    objeto_tipo="",
    objeto_id=None,
    total_bytes=0,
    sha256="",
):
    """
    Construye una representación uniforme de un evento
    histórico de Espaciómetro.
    """

    total_bytes = int(
        total_bytes
        or 0
    )

    return {
        "fecha": fecha,

        "etapa": etapa,

        "codigo": codigo,

        "titulo": titulo,

        "estado": (
            str(
                estado
                or ""
            )
        ),

        "usuario": (
            str(
                usuario
                or ""
            )
        ),

        "detalle": (
            str(
                detalle
                or ""
            )
        ),

        "objeto_tipo": objeto_tipo,

        "objeto_id": objeto_id,

        "total_bytes": total_bytes,

        "total_legible": (
            bytes_legibles(
                total_bytes
            )
        ),

        "sha256": (
            str(
                sha256
                or ""
            )
        ),
    }


def _fecha_orden(evento):
    """
    Los eventos reales poseen fecha.

    Se mantiene esta función separada para hacer
    explícito el criterio temporal.
    """

    return evento.get(
        "fecha"
    )


# =============================================================================
# ESTADO DEL CICLO
# =============================================================================


def _evaluar_estado_ciclo(
    *,
    lote,
    respaldos,
    descargas,
    liberaciones,
    retiros,
):
    """
    Resume el estado alcanzado por un lote.

    Un ciclo ESP012 -> ESP015 se considera completamente
    cerrado cuando existe evidencia de:

    - lote LIBERADO;
    - respaldo LISTO;
    - descarga VERIFICADA;
    - liberación COMPLETADA;
    - retiro del ZIP COMPLETADO.
    """

    respaldo_listo = any(
        respaldo.estado
        == RespaldoMantenimiento.Estado.LISTO

        for respaldo
        in respaldos
    )


    descarga_verificada = any(
        descarga.estado
        == RegistroDescargaRespaldo.Estado.VERIFICADA

        for descarga
        in descargas
    )


    liberacion_completa = any(
        liberacion.estado
        == LiberacionMantenimiento.Estado.COMPLETADA

        for liberacion
        in liberaciones
    )


    retiro_completo = any(
        retiro.estado
        == RetiroRespaldoServidor.Estado.COMPLETADO

        for retiro
        in retiros
    )


    lote_liberado = (
        lote.estado
        == LoteCandidatosMantenimiento.Estado.LIBERADO
    )


    ciclo_completo = all(
        [
            lote_liberado,
            respaldo_listo,
            descarga_verificada,
            liberacion_completa,
            retiro_completo,
        ]
    )


    return {
        "lote_liberado": lote_liberado,

        "respaldo_listo": respaldo_listo,

        "descarga_verificada": descarga_verificada,

        "liberacion_completa": liberacion_completa,

        "retiro_completo": retiro_completo,

        "ciclo_completo": ciclo_completo,
    }


# =============================================================================
# AUDITORÍA DE UN LOTE
# =============================================================================


def construir_auditoria_lote(
    lote,
    *,
    incluir_candidatos=True,
):
    """
    Reconstruye la historia completa de un lote.

    Solamente consulta la base de datos.
    """

    candidatos = list(
        CandidatoMantenimiento
        .objects
        .filter(
            lote=lote
        )
        .select_related(
            "ruta_monitoreada"
        )
        .order_by(
            "id"
        )
    )


    respaldos = list(
        RespaldoMantenimiento
        .objects
        .filter(
            lote=lote
        )
        .order_by(
            "creado_en",
            "id",
        )
    )


    respaldo_ids = [
        respaldo.pk
        for respaldo
        in respaldos
    ]


    if respaldo_ids:

        descargas = list(
            RegistroDescargaRespaldo
            .objects
            .filter(
                respaldo_id__in=(
                    respaldo_ids
                )
            )
            .select_related(
                "respaldo"
            )
            .order_by(
                "iniciada_en",
                "id",
            )
        )


        retiros = list(
            RetiroRespaldoServidor
            .objects
            .filter(
                respaldo_id__in=(
                    respaldo_ids
                )
            )
            .select_related(
                "respaldo",
                "liberacion",
                "descarga_verificada",
            )
            .order_by(
                "iniciado_en",
                "id",
            )
        )

    else:

        descargas = []

        retiros = []


    liberaciones = list(
        LiberacionMantenimiento
        .objects
        .filter(
            lote=lote
        )
        .select_related(
            "respaldo",
            "descarga_verificada",
        )
        .order_by(
            "iniciado_en",
            "id",
        )
    )


    eventos = []


    # =========================================================================
    # ESP012 — CREACIÓN DEL LOTE
    # =========================================================================

    eventos.append(
        _evento(
            fecha=lote.creado_en,

            etapa="ESP012",

            codigo="LOTE_CREADO",

            titulo="Lote de candidatos creado",

            estado=lote.estado,

            usuario=lote.creado_por,

            detalle=(
                f"{lote.total_archivos} archivo(s) "
                f"seleccionado(s)."
            ),

            objeto_tipo=(
                "LoteCandidatosMantenimiento"
            ),

            objeto_id=lote.pk,

            total_bytes=lote.total_bytes,
        )
    )


    # =========================================================================
    # ESP013 — RESPALDOS
    # =========================================================================

    for respaldo in respaldos:

        detalle = (
            f"{respaldo.incluidos} incluido(s) · "
            f"{respaldo.omitidos} omitido(s)"
        )


        eventos.append(
            _evento(
                fecha=respaldo.creado_en,

                etapa="ESP013",

                codigo="RESPALDO",

                titulo=(
                    f"Respaldo #{respaldo.pk}"
                ),

                estado=respaldo.estado,

                usuario=respaldo.creado_por,

                detalle=detalle,

                objeto_tipo=(
                    "RespaldoMantenimiento"
                ),

                objeto_id=respaldo.pk,

                total_bytes=(
                    respaldo.total_bytes_paquete
                ),

                sha256=respaldo.sha256,
            )
        )


    # =========================================================================
    # ESP014 — DESCARGAS
    # =========================================================================

    for descarga in descargas:

        eventos.append(
            _evento(
                fecha=descarga.iniciada_en,

                etapa="ESP014",

                codigo="DESCARGA_INICIADA",

                titulo=(
                    f"Descarga #{descarga.pk} iniciada"
                ),

                estado=descarga.estado,

                usuario=descarga.usuario,

                detalle=(
                    "El servidor validó el paquete "
                    "e inició su entrega."
                ),

                objeto_tipo=(
                    "RegistroDescargaRespaldo"
                ),

                objeto_id=descarga.pk,

                total_bytes=descarga.total_bytes,

                sha256=(
                    descarga.sha256_servidor
                    or descarga.sha256_esperado
                ),
            )
        )


        if descarga.confirmada_en:

            if (
                descarga.estado
                == RegistroDescargaRespaldo
                .Estado
                .VERIFICADA
            ):

                titulo = (
                    f"Descarga #{descarga.pk} "
                    "verificada por SHA-256"
                )

            else:

                titulo = (
                    f"Descarga #{descarga.pk} "
                    "confirmada"
                )


            eventos.append(
                _evento(
                    fecha=descarga.confirmada_en,

                    etapa="ESP014",

                    codigo="DESCARGA_CONFIRMADA",

                    titulo=titulo,

                    estado=descarga.estado,

                    usuario=descarga.usuario,

                    detalle=descarga.detalle,

                    objeto_tipo=(
                        "RegistroDescargaRespaldo"
                    ),

                    objeto_id=descarga.pk,

                    total_bytes=descarga.total_bytes,

                    sha256=(
                        descarga.sha256_cliente
                        or descarga.sha256_servidor
                    ),
                )
            )


    # =========================================================================
    # ESP015 — LIBERACIONES
    # =========================================================================

    for liberacion in liberaciones:

        fecha = (
            liberacion.finalizado_en
            or liberacion.iniciado_en
        )


        eventos.append(
            _evento(
                fecha=fecha,

                etapa="ESP015",

                codigo="LIBERACION_ORIGINALES",

                titulo=(
                    f"Liberación #{liberacion.pk} "
                    "de originales"
                ),

                estado=liberacion.estado,

                usuario=liberacion.usuario,

                detalle=(
                    f"{liberacion.liberados} liberado(s) · "
                    f"{liberacion.omitidos} omitido(s)"
                ),

                objeto_tipo=(
                    "LiberacionMantenimiento"
                ),

                objeto_id=liberacion.pk,

                total_bytes=(
                    liberacion.total_bytes_liberados
                ),
            )
        )


    # =========================================================================
    # ESP015 — RETIRO DEL ZIP DEL SERVIDOR
    # =========================================================================

    for retiro in retiros:

        fecha = (
            retiro.finalizado_en
            or retiro.iniciado_en
        )


        eventos.append(
            _evento(
                fecha=fecha,

                etapa="ESP015",

                codigo="RETIRO_ZIP_SERVIDOR",

                titulo=(
                    f"Retiro ZIP #{retiro.pk} "
                    "del servidor"
                ),

                estado=retiro.estado,

                usuario=retiro.usuario,

                detalle=retiro.detalle,

                objeto_tipo=(
                    "RetiroRespaldoServidor"
                ),

                objeto_id=retiro.pk,

                total_bytes=(
                    retiro.total_bytes_snapshot
                ),

                sha256=(
                    retiro.sha256_snapshot
                ),
            )
        )


    # =========================================================================
    # ORDEN CRONOLÓGICO
    # =========================================================================

    eventos = sorted(
        eventos,
        key=_fecha_orden,
    )


    # =========================================================================
    # ESTADO DEL CICLO
    # =========================================================================

    estado_ciclo = (
        _evaluar_estado_ciclo(
            lote=lote,

            respaldos=respaldos,

            descargas=descargas,

            liberaciones=liberaciones,

            retiros=retiros,
        )
    )


    # =========================================================================
    # ESPACIO LIBERADO
    # =========================================================================

    total_originales_liberados = sum(
        int(
            liberacion.total_bytes_liberados
            or 0
        )

        for liberacion
        in liberaciones

        if (
            liberacion.estado
            in {
                LiberacionMantenimiento
                .Estado
                .COMPLETADA,

                LiberacionMantenimiento
                .Estado
                .PARCIAL,
            }
        )
    )


    total_zip_retirado = sum(
        int(
            retiro.total_bytes_snapshot
            or 0
        )

        for retiro
        in retiros

        if (
            retiro.estado
            == RetiroRespaldoServidor
            .Estado
            .COMPLETADO
        )
    )


    total_retirado_servidor = (
        total_originales_liberados
        +
        total_zip_retirado
    )


    resultado = {
        "lote": lote,

        "eventos": eventos,

        "estado_ciclo": estado_ciclo,

        "respaldos": respaldos,

        "descargas": descargas,

        "liberaciones": liberaciones,

        "retiros": retiros,

        "total_originales_liberados": (
            total_originales_liberados
        ),

        "total_originales_liberados_legible": (
            bytes_legibles(
                total_originales_liberados
            )
        ),

        "total_zip_retirado": (
            total_zip_retirado
        ),

        "total_zip_retirado_legible": (
            bytes_legibles(
                total_zip_retirado
            )
        ),

        "total_retirado_servidor": (
            total_retirado_servidor
        ),

        "total_retirado_servidor_legible": (
            bytes_legibles(
                total_retirado_servidor
            )
        ),
    }


    if incluir_candidatos:

        resultado[
            "candidatos"
        ] = candidatos


    return resultado


# =============================================================================
# AUDITORÍA GENERAL
# =============================================================================


def construir_auditoria_general(
    *,
    limite=100,
):
    """
    Devuelve los lotes más recientes con un resumen
    de auditoría.

    No realiza escaneo de archivos.
    """

    try:

        limite = int(
            limite
        )

    except (
        TypeError,
        ValueError,
    ):

        limite = 100


    limite = max(
        1,
        min(
            limite,
            500,
        ),
    )


    lotes = list(
        LoteCandidatosMantenimiento
        .objects
        .all()
        .order_by(
            "-creado_en",
            "-id",
        )[
            :limite
        ]
    )


    resultados = []


    total_originales = 0

    total_zip = 0

    ciclos_completos = 0


    for lote in lotes:

        auditoria = (
            construir_auditoria_lote(
                lote,
                incluir_candidatos=False,
            )
        )


        resultados.append(
            auditoria
        )


        total_originales += (
            auditoria[
                "total_originales_liberados"
            ]
        )


        total_zip += (
            auditoria[
                "total_zip_retirado"
            ]
        )


        if (
            auditoria[
                "estado_ciclo"
            ][
                "ciclo_completo"
            ]
        ):

            ciclos_completos += 1


    return {
        "lotes": resultados,

        "total_lotes": len(
            resultados
        ),

        "ciclos_completos": (
            ciclos_completos
        ),

        "total_originales_liberados": (
            total_originales
        ),

        "total_originales_liberados_legible": (
            bytes_legibles(
                total_originales
            )
        ),

        "total_zip_retirado": (
            total_zip
        ),

        "total_zip_retirado_legible": (
            bytes_legibles(
                total_zip
            )
        ),

        "total_retirado_servidor": (
            total_originales
            +
            total_zip
        ),

        "total_retirado_servidor_legible": (
            bytes_legibles(
                total_originales
                +
                total_zip
            )
        ),

        "limite": limite,
    }