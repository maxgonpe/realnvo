from __future__ import annotations

import os
import stat as statmod

from pathlib import Path

from django.db import transaction
from django.utils import timezone

from .candidates import (
    _estado_actual_candidato,
    _resolver_archivo_candidato,
)
from .downloads import (
    validar_integridad_respaldo,
)
from .models import (
    CandidatoMantenimiento,
    DetalleLiberacionMantenimiento,
    DetalleRespaldoMantenimiento,
    LiberacionMantenimiento,
    LoteCandidatosMantenimiento,
    RegistroDescargaRespaldo,
    RespaldoMantenimiento,
    bytes_legibles,
)


# =============================================================================
# FRASE DE CONFIRMACIÓN
# =============================================================================


def frase_confirmacion_lote(
    lote,
) -> str:

    return (
        f"LIBERAR LOTE {lote.pk}"
    )


# =============================================================================
# SNAPSHOT
# =============================================================================


def _stat_coincide_snapshot(
    candidato: CandidatoMantenimiento,
    info,
) -> bool:

    if int(
        info.st_size
    ) != int(
        candidato.total_bytes_snapshot
    ):

        return False


    if int(
        info.st_mtime_ns
    ) != int(
        candidato.mtime_ns_snapshot
    ):

        return False


    inode = max(
        int(
            getattr(
                info,
                "st_ino",
                0,
            )
        ),
        0,
    )


    dispositivo = max(
        int(
            getattr(
                info,
                "st_dev",
                0,
            )
        ),
        0,
    )


    if (
        candidato.inode_snapshot
        and inode
        != candidato.inode_snapshot
    ):

        return False


    if (
        candidato.dispositivo_snapshot
        and dispositivo
        != candidato.dispositivo_snapshot
    ):

        return False


    return True


# =============================================================================
# RESPALDO + DESCARGA VERIFICADA
# =============================================================================


def _obtener_respaldo_y_descarga(
    lote,
):

    respaldos = (
        lote.respaldos
        .filter(
            estado=(
                RespaldoMantenimiento
                .Estado
                .LISTO
            )
        )
        .order_by(
            "-creado_en",
            "-id",
        )
    )


    primer_respaldo = None


    for respaldo in respaldos:

        if primer_respaldo is None:

            primer_respaldo = (
                respaldo
            )


        descarga = (
            respaldo.descargas
            .filter(
                estado=(
                    RegistroDescargaRespaldo
                    .Estado
                    .VERIFICADA
                )
            )
            .order_by(
                "-confirmada_en",
                "-id",
            )
            .first()
        )


        if descarga:

            return (
                respaldo,
                descarga,
            )


    return (
        primer_respaldo,
        None,
    )


# =============================================================================
# CONDICIÓN
# =============================================================================


def _condicion(
    codigo,
    nombre,
    cumple,
    detalle,
):

    return {
        "codigo": codigo,
        "nombre": nombre,
        "cumple": bool(
            cumple
        ),
        "detalle": detalle,
    }


# =============================================================================
# EVALUAR
# =============================================================================


def evaluar_liberacion_lote(
    lote,
) -> dict:
    """
    Evaluación completamente de solo lectura.

    NO elimina, mueve ni modifica archivos.
    """

    resultado = {
        "lote": lote,

        "apto": False,

        "condiciones": [],

        "candidatos": [],

        "respaldo": None,

        "descarga": None,

        "total_archivos": 0,

        "total_bytes": 0,

        "total_legible": "0 B",

        "frase_confirmacion": (
            frase_confirmacion_lote(
                lote
            )
        ),
    }


    candidatos = list(
        lote.candidatos
        .select_related(
            "ruta_monitoreada"
        )
        .order_by(
            "ruta_monitoreada__nombre",
            "ruta_relativa",
        )
    )


    resultado[
        "total_archivos"
    ] = len(
        candidatos
    )


    total_bytes = sum(
        int(
            candidato
            .total_bytes_snapshot
        )
        for candidato
        in candidatos
    )


    resultado[
        "total_bytes"
    ] = total_bytes


    resultado[
        "total_legible"
    ] = bytes_legibles(
        total_bytes
    )


    # =========================================================================
    # ESTADO DEL LOTE
    # =========================================================================

    lote_preparado = (
        lote.estado
        == LoteCandidatosMantenimiento
        .Estado
        .PREPARADO
    )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "LOTE_PREPARADO",
            "Lote preparado",
            lote_preparado,
            (
                "El lote debe estar en estado "
                "PREPARADO."
            ),
        )
    )


    # =========================================================================
    # CANDIDATOS
    # =========================================================================

    tiene_candidatos = bool(
        candidatos
    )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "TIENE_CANDIDATOS",
            "Lote con candidatos",
            tiene_candidatos,
            (
                f"{len(candidatos)} "
                "archivo(s) registrado(s)."
            ),
        )
    )


    # =========================================================================
    # RESPALDO Y DESCARGA
    # =========================================================================

    (
        respaldo,
        descarga,
    ) = (
        _obtener_respaldo_y_descarga(
            lote
        )
    )


    resultado[
        "respaldo"
    ] = respaldo


    resultado[
        "descarga"
    ] = descarga


    respaldo_listo = (
        respaldo is not None
        and respaldo.estado
        == RespaldoMantenimiento
        .Estado
        .LISTO
    )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "RESPALDO_LISTO",
            "Respaldo completo",
            respaldo_listo,
            (
                (
                    f"Respaldo "
                    f"#{respaldo.pk} LISTO."
                )
                if respaldo
                else
                "No existe respaldo LISTO."
            ),
        )
    )


    descarga_verificada = (
        descarga is not None
    )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "DESCARGA_VERIFICADA",
            "Descarga verificada",
            descarga_verificada,
            (
                (
                    f"Descarga "
                    f"#{descarga.pk} "
                    "verificada mediante SHA-256."
                )
                if descarga
                else
                (
                    "No existe una descarga "
                    "ESP014 verificada."
                )
            ),
        )
    )


    # =========================================================================
    # INTEGRIDAD DEL RESPALDO EN EL SERVIDOR
    # =========================================================================

    integridad_respaldo = False

    detalle_integridad = (
        "No existe respaldo verificable."
    )


    if respaldo_listo:

        try:

            validacion = (
                validar_integridad_respaldo(
                    respaldo
                )
            )


            integridad_respaldo = True


            detalle_integridad = (
                "SHA-256 del ZIP coincide "
                "con ESP013: "
                f"{validacion['sha256']}"
            )


        except Exception as exc:

            detalle_integridad = str(
                exc
            )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "INTEGRIDAD_RESPALDO",
            "Integridad del ZIP",
            integridad_respaldo,
            detalle_integridad,
        )
    )


    # =========================================================================
    # RESPALDO CONTIENE EXACTAMENTE LOS CANDIDATOS
    # =========================================================================

    cobertura_completa = False

    detalle_cobertura = (
        "No fue posible comprobar "
        "la cobertura del respaldo."
    )


    if respaldo:

        ids_candidatos = {
            candidato.pk
            for candidato
            in candidatos
        }


        ids_incluidos = set(
            respaldo.detalles
            .filter(
                estado=(
                    DetalleRespaldoMantenimiento
                    .Estado
                    .INCLUIDO
                )
            )
            .values_list(
                "candidato_id",
                flat=True,
            )
        )


        cobertura_completa = (
            respaldo.omitidos == 0
            and respaldo.incluidos
            == len(
                candidatos
            )
            and ids_incluidos
            == ids_candidatos
        )


        detalle_cobertura = (
            f"Esperados: "
            f"{len(candidatos)} · "
            f"Incluidos: "
            f"{respaldo.incluidos} · "
            f"Omitidos: "
            f"{respaldo.omitidos}"
        )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "COBERTURA_COMPLETA",
            "Cobertura completa",
            cobertura_completa,
            detalle_cobertura,
        )
    )


    # =========================================================================
    # PERMISOS DE RUTA
    # =========================================================================

    rutas_autorizadas = (
        tiene_candidatos
        and all(
            candidato
            .ruta_monitoreada
            .permite_mantenimiento
            for candidato
            in candidatos
        )
    )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "RUTAS_AUTORIZADAS",
            "Rutas autorizadas",
            rutas_autorizadas,
            (
                "Todas las rutas permiten mantenimiento."
                if rutas_autorizadas
                else
                (
                    "Una o más rutas no tienen "
                    "permite_mantenimiento activado."
                )
            ),
        )
    )


    # =========================================================================
    # ESTADO ACTUAL DE CADA ARCHIVO
    # =========================================================================

    todos_vigentes = (
        tiene_candidatos
    )


    sin_hardlinks = (
        tiene_candidatos
    )


    for candidato in candidatos:

        estado = (
            _estado_actual_candidato(
                candidato
            )
        )


        vigente = (
            estado[
                "codigo"
            ] == "VIGENTE"
        )


        hardlinks_ok = False

        enlaces = None


        if vigente:

            try:

                (
                    path,
                    info,
                ) = (
                    _resolver_archivo_candidato(
                        candidato
                        .ruta_monitoreada,

                        candidato
                        .ruta_relativa,
                    )
                )


                enlaces = int(
                    getattr(
                        info,
                        "st_nlink",
                        0,
                    )
                )


                hardlinks_ok = (
                    enlaces == 1
                )


            except Exception as exc:

                vigente = False

                estado = {
                    "codigo": "PROBLEMA",

                    "detalle": str(
                        exc
                    ),
                }


        if not vigente:

            todos_vigentes = False


        if not hardlinks_ok:

            sin_hardlinks = False


        resultado[
            "candidatos"
        ].append(
            {
                "candidato": candidato,

                "estado": (
                    estado[
                        "codigo"
                    ]
                ),

                "detalle": (
                    estado[
                        "detalle"
                    ]
                ),

                "vigente": vigente,

                "mantenimiento": (
                    candidato
                    .ruta_monitoreada
                    .permite_mantenimiento
                ),

                "hardlinks_ok": (
                    hardlinks_ok
                ),

                "enlaces": enlaces,
            }
        )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "TODOS_VIGENTES",
            "Originales sin cambios",
            todos_vigentes,
            (
                "Todos los candidatos siguen "
                "coincidiendo con ESP012."
                if todos_vigentes
                else
                (
                    "Uno o más candidatos "
                    "cambiaron, desaparecieron "
                    "o presentan problemas."
                )
            ),
        )
    )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "SIN_HARDLINKS",
            "Sin enlaces duros",
            sin_hardlinks,
            (
                "Todos los archivos poseen "
                "un único enlace físico."
                if sin_hardlinks
                else
                (
                    "Se detectó al menos un "
                    "archivo con hardlinks."
                )
            ),
        )
    )


    # =========================================================================
    # RESULTADO GLOBAL
    # =========================================================================

    resultado[
        "apto"
    ] = all(
        item[
            "cumple"
        ]
        for item
        in resultado[
            "condiciones"
        ]
    )


    return resultado


# =============================================================================
# PREFLIGHT INDIVIDUAL
# =============================================================================


def _preflight_candidato(
    candidato,
) -> Path:

    if not (
        candidato
        .ruta_monitoreada
        .permite_mantenimiento
    ):

        raise RuntimeError(
            "La ruta ya no permite mantenimiento."
        )


    if not (
        candidato
        .ruta_monitoreada
        .activa
    ):

        raise RuntimeError(
            "La ruta monitoreada ya no está activa."
        )


    estado = (
        _estado_actual_candidato(
            candidato
        )
    )


    if estado[
        "codigo"
    ] != "VIGENTE":

        raise RuntimeError(
            (
                "El candidato ya no está vigente: "
                f"{estado['detalle']}"
            )
        )


    (
        path,
        info,
    ) = (
        _resolver_archivo_candidato(

            candidato
            .ruta_monitoreada,

            candidato
            .ruta_relativa,
        )
    )


    if not statmod.S_ISREG(
        info.st_mode
    ):

        raise RuntimeError(
            "La ubicación ya no corresponde "
            "a un archivo regular."
        )


    if not _stat_coincide_snapshot(
        candidato,
        info,
    ):

        raise RuntimeError(
            "El archivo ya no coincide "
            "con el snapshot ESP012."
        )


    if int(
        getattr(
            info,
            "st_nlink",
            0,
        )
    ) != 1:

        raise RuntimeError(
            "El archivo posee enlaces duros "
            "y ESP015 no lo eliminará."
        )


    return path


# =============================================================================
# ELIMINACIÓN SEGURA INDIVIDUAL
# =============================================================================


def _eliminar_candidato_seguro(
    candidato,
) -> int:
    """
    Revalida inmediatamente antes de unlink.

    Usa descriptores del directorio y O_NOFOLLOW
    cuando el sistema operativo lo soporta.
    """

    path = (
        _preflight_candidato(
            candidato
        )
    )


    flags_directorio = os.O_RDONLY


    if hasattr(
        os,
        "O_DIRECTORY",
    ):

        flags_directorio |= (
            os.O_DIRECTORY
        )


    if hasattr(
        os,
        "O_NOFOLLOW",
    ):

        flags_directorio |= (
            os.O_NOFOLLOW
        )


    parent_fd = os.open(
        str(
            path.parent
        ),
        flags_directorio,
    )


    archivo_fd = None


    try:

        flags_archivo = os.O_RDONLY


        if hasattr(
            os,
            "O_NOFOLLOW",
        ):

            flags_archivo |= (
                os.O_NOFOLLOW
            )


        archivo_fd = os.open(
            path.name,
            flags_archivo,
            dir_fd=parent_fd,
        )


        info_fd = os.fstat(
            archivo_fd
        )


        if not statmod.S_ISREG(
            info_fd.st_mode
        ):

            raise RuntimeError(
                "El objetivo dejó de ser "
                "un archivo regular."
            )


        if not _stat_coincide_snapshot(
            candidato,
            info_fd,
        ):

            raise RuntimeError(
                "El archivo cambió justo antes "
                "de la eliminación."
            )


        if int(
            getattr(
                info_fd,
                "st_nlink",
                0,
            )
        ) != 1:

            raise RuntimeError(
                "El número de enlaces físicos "
                "cambió antes de eliminar."
            )


        info_nombre = os.stat(
            path.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )


        if not statmod.S_ISREG(
            info_nombre.st_mode
        ):

            raise RuntimeError(
                "La ruta dejó de apuntar "
                "a un archivo regular."
            )


        if (
            int(
                info_nombre.st_ino
            )
            != int(
                info_fd.st_ino
            )
            or
            int(
                info_nombre.st_dev
            )
            != int(
                info_fd.st_dev
            )
        ):

            raise RuntimeError(
                "La identidad física del archivo "
                "cambió durante la operación."
            )


        if not _stat_coincide_snapshot(
            candidato,
            info_nombre,
        ):

            raise RuntimeError(
                "La ruta ya no coincide "
                "con el snapshot ESP012."
            )


        total_bytes = int(
            info_fd.st_size
        )


        os.unlink(
            path.name,
            dir_fd=parent_fd,
        )


        return total_bytes


    finally:

        if archivo_fd is not None:

            os.close(
                archivo_fd
            )


        os.close(
            parent_fd
        )


# =============================================================================
# EJECUTAR LIBERACIÓN
# =============================================================================


def ejecutar_liberacion_lote(
    *,
    lote,
    usuario="",
    confirmacion="",
) -> dict:

    resultado = {
        "liberacion": None,

        "error": "",

        "estado": "",

        "liberados": 0,

        "omitidos": 0,

        "bytes_liberados": 0,
    }


    esperada = (
        frase_confirmacion_lote(
            lote
        )
    )


    confirmacion = str(
        confirmacion
        or ""
    ).strip()


    if confirmacion != esperada:

        resultado[
            "error"
        ] = (
            "La frase de confirmación "
            "no coincide."
        )

        return resultado


    # =========================================================================
    # EVALUACIÓN COMPLETA ANTES DE TOMAR EL BLOQUEO
    # =========================================================================

    evaluacion = (
        evaluar_liberacion_lote(
            lote
        )
    )


    if not evaluacion[
        "apto"
    ]:

        resultado[
            "error"
        ] = (
            "El lote ya no cumple todas "
            "las condiciones de liberación."
        )

        return resultado


    respaldo = (
        evaluacion[
            "respaldo"
        ]
    )


    descarga = (
        evaluacion[
            "descarga"
        ]
    )


    # =========================================================================
    # BLOQUEO LÓGICO
    # =========================================================================

    with transaction.atomic():

        lote_bloqueado = (
            LoteCandidatosMantenimiento
            .objects
            .select_for_update()
            .get(
                pk=lote.pk
            )
        )


        if (
            lote_bloqueado.estado
            != LoteCandidatosMantenimiento
            .Estado
            .PREPARADO
        ):

            resultado[
                "error"
            ] = (
                "El lote dejó de estar "
                "en estado PREPARADO."
            )

            return resultado


        lote_bloqueado.estado = (
            LoteCandidatosMantenimiento
            .Estado
            .LIBERANDO
        )


        lote_bloqueado.save(
            update_fields=[
                "estado",
            ]
        )


        liberacion = (
            LiberacionMantenimiento
            .objects
            .create(

                lote=lote_bloqueado,

                respaldo=respaldo,

                descarga_verificada=(
                    descarga
                ),

                estado=(
                    LiberacionMantenimiento
                    .Estado
                    .EJECUTANDO
                ),

                usuario=(
                    str(
                        usuario
                        or ""
                    )[
                        :150
                    ]
                ),

                total_candidatos=(
                    evaluacion[
                        "total_archivos"
                    ]
                ),

                total_bytes_objetivo=(
                    evaluacion[
                        "total_bytes"
                    ]
                ),

                confirmacion=(
                    confirmacion[
                        :100
                    ]
                ),
            )
        )


    resultado[
        "liberacion"
    ] = liberacion


    # =========================================================================
    # VOLVER A CARGAR CANDIDATOS
    # =========================================================================

    candidatos = list(
        lote.candidatos
        .select_related(
            "ruta_monitoreada"
        )
        .order_by(
            "ruta_monitoreada__nombre",
            "ruta_relativa",
        )
    )


    # =========================================================================
    # PREFLIGHT COMPLETO
    #
    # MUY IMPORTANTE:
    # no se elimina nada hasta que TODOS pasen esta etapa.
    # =========================================================================

    try:

        # Revalidamos incluso el ZIP otra vez.

        validar_integridad_respaldo(
            respaldo
        )


        for candidato in candidatos:

            _preflight_candidato(
                candidato
            )


    except Exception as exc:

        liberacion.estado = (
            LiberacionMantenimiento
            .Estado
            .ERROR
        )


        liberacion.errores = [
            str(
                exc
            )
        ]


        liberacion.finalizado_en = (
            timezone.now()
        )


        liberacion.save(
            update_fields=[
                "estado",
                "errores",
                "finalizado_en",
            ]
        )


        lote.estado = (
            LoteCandidatosMantenimiento
            .Estado
            .PREPARADO
        )


        lote.save(
            update_fields=[
                "estado",
            ]
        )


        resultado[
            "error"
        ] = (
            "El preflight final bloqueó "
            f"la liberación: {exc}"
        )


        resultado[
            "estado"
        ] = liberacion.estado


        return resultado


    # =========================================================================
    # CREAR TRAZA ANTES DE TOCAR EL SISTEMA DE ARCHIVOS
    # =========================================================================

    detalles = {}


    for candidato in candidatos:

        detalle = (
            DetalleLiberacionMantenimiento
            .objects
            .create(

                liberacion=liberacion,

                candidato=candidato,

                estado=(
                    DetalleLiberacionMantenimiento
                    .Estado
                    .PENDIENTE
                ),

                ruta_relativa=(
                    candidato
                    .ruta_relativa
                ),

                total_bytes_snapshot=(
                    candidato
                    .total_bytes_snapshot
                ),

                motivo=(
                    "Pendiente de liberación."
                ),
            )
        )


        detalles[
            candidato.pk
        ] = detalle


    # =========================================================================
    # ELIMINAR
    # =========================================================================

    liberados = 0

    bytes_liberados = 0

    errores = []

    fallo = False


    for indice, candidato in enumerate(
        candidatos
    ):

        detalle = detalles[
            candidato.pk
        ]


        if fallo:

            detalle.estado = (
                DetalleLiberacionMantenimiento
                .Estado
                .OMITIDO
            )


            detalle.motivo = (
                "No se intentó eliminar porque "
                "la liberación fue detenida "
                "tras un error anterior."
            )


            detalle.save(
                update_fields=[
                    "estado",
                    "motivo",
                ]
            )


            continue


        try:

            liberados_bytes_archivo = (
                _eliminar_candidato_seguro(
                    candidato
                )
            )


            liberados += 1


            bytes_liberados += (
                liberados_bytes_archivo
            )


            detalle.estado = (
                DetalleLiberacionMantenimiento
                .Estado
                .LIBERADO
            )


            detalle.motivo = (
                "Archivo original eliminado "
                "después de revalidar ESP012, "
                "ESP013 y ESP014."
            )


            detalle.liberado_en = (
                timezone.now()
            )


            detalle.save(
                update_fields=[
                    "estado",
                    "motivo",
                    "liberado_en",
                ]
            )


        except Exception as exc:

            fallo = True


            mensaje = (
                f"{candidato.ruta_relativa}: "
                f"{exc}"
            )


            errores.append(
                mensaje
            )


            detalle.estado = (
                DetalleLiberacionMantenimiento
                .Estado
                .ERROR
            )


            detalle.motivo = (
                str(
                    exc
                )
            )


            detalle.save(
                update_fields=[
                    "estado",
                    "motivo",
                ]
            )


    total = len(
        candidatos
    )


    omitidos = (
        total
        - liberados
    )


    # =========================================================================
    # RESULTADO FINAL
    # =========================================================================

    if (
        liberados == total
        and total > 0
    ):

        estado_liberacion = (
            LiberacionMantenimiento
            .Estado
            .COMPLETADA
        )


        estado_lote = (
            LoteCandidatosMantenimiento
            .Estado
            .LIBERADO
        )


    elif liberados > 0:

        estado_liberacion = (
            LiberacionMantenimiento
            .Estado
            .PARCIAL
        )


        estado_lote = (
            LoteCandidatosMantenimiento
            .Estado
            .LIBERACION_PARCIAL
        )


    else:

        estado_liberacion = (
            LiberacionMantenimiento
            .Estado
            .ERROR
        )


        estado_lote = (
            LoteCandidatosMantenimiento
            .Estado
            .PREPARADO
        )


    liberacion.estado = (
        estado_liberacion
    )


    liberacion.liberados = (
        liberados
    )


    liberacion.omitidos = (
        omitidos
    )


    liberacion.total_bytes_liberados = (
        bytes_liberados
    )


    liberacion.errores = (
        errores
    )


    liberacion.finalizado_en = (
        timezone.now()
    )


    liberacion.save(
        update_fields=[
            "estado",
            "liberados",
            "omitidos",
            "total_bytes_liberados",
            "errores",
            "finalizado_en",
        ]
    )


    lote.estado = (
        estado_lote
    )


    lote.save(
        update_fields=[
            "estado",
        ]
    )


    resultado[
        "estado"
    ] = liberacion.estado


    resultado[
        "liberados"
    ] = liberados


    resultado[
        "omitidos"
    ] = omitidos


    resultado[
        "bytes_liberados"
    ] = bytes_liberados


    if errores:

        resultado[
            "error"
        ] = (
            "La liberación no pudo completarse "
            "para todos los archivos."
        )


    return resultado


# =============================================================================
# DETALLE
# =============================================================================


def obtener_detalle_liberacion(
    liberacion,
):

    detalles = list(
        liberacion.detalles
        .select_related(
            "candidato",
            "candidato__ruta_monitoreada",
        )
        .order_by(
            "candidato__ruta_monitoreada__nombre",
            "ruta_relativa",
        )
    )


    return {
        "liberacion": liberacion,

        "detalles": detalles,

        "liberados": sum(
            1
            for item
            in detalles
            if item.estado
            == DetalleLiberacionMantenimiento
            .Estado
            .LIBERADO
        ),

        "errores": sum(
            1
            for item
            in detalles
            if item.estado
            == DetalleLiberacionMantenimiento
            .Estado
            .ERROR
        ),
    }