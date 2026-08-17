from __future__ import annotations

import hashlib
import os
import stat as statmod

from contextlib import contextmanager
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from .backup import (
    obtener_directorio_respaldos,
)
from .downloads import (
    normalizar_sha256,
)
from .models import (
    LiberacionMantenimiento,
    LoteCandidatosMantenimiento,
    RegistroDescargaRespaldo,
    RespaldoMantenimiento,
    RetiroRespaldoServidor,
    bytes_legibles,
)


TAMANO_BLOQUE = (
    1024
    * 1024
)


# =============================================================================
# CONFIRMACIÓN
# =============================================================================


def frase_confirmacion_retiro(
    respaldo,
):

    return (
        f"RETIRAR RESPALDO {respaldo.pk}"
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
# RUTA DEL ZIP
# =============================================================================


def _resolver_ruta_zip(
    respaldo,
):

    relativa_texto = str(
        respaldo.ruta_relativa_archivo
        or ""
    ).strip()


    if not relativa_texto:

        raise RuntimeError(
            "El respaldo no tiene una ruta "
            "física registrada."
        )


    relativa = Path(
        relativa_texto
    )


    if relativa.is_absolute():

        raise RuntimeError(
            "La ruta del respaldo no puede "
            "ser absoluta."
        )


    if not relativa.parts:

        raise RuntimeError(
            "La ruta del respaldo está vacía."
        )


    for parte in relativa.parts:

        if parte in {
            "",
            ".",
            "..",
        }:

            raise RuntimeError(
                "La ruta contiene componentes "
                "no permitidos."
            )


    base = (
        obtener_directorio_respaldos()
    )


    # -------------------------------------------------------------------------
    # Ningún componente puede ser symlink.
    # -------------------------------------------------------------------------

    actual = base


    for parte in relativa.parts:

        actual = (
            actual
            / parte
        )


        if (
            actual.exists()
            and actual.is_symlink()
        ):

            raise RuntimeError(
                "La ruta del respaldo contiene "
                "un enlace simbólico."
            )


    try:

        path = (
            (
                base
                / relativa
            )
            .resolve(
                strict=True
            )
        )


    except (
        FileNotFoundError,
        OSError,
    ) as exc:

        raise RuntimeError(
            "El ZIP físico ya no existe."
        ) from exc


    try:

        path.relative_to(
            base
        )


    except ValueError as exc:

        raise RuntimeError(
            "El ZIP está fuera del área privada "
            "de Espaciómetro."
        ) from exc


    return (
        base,
        path,
    )


# =============================================================================
# ABRIR ZIP DE FORMA SEGURA
# =============================================================================


@contextmanager
def _abrir_zip_seguro(
    respaldo,
):
    """
    Abre el ZIP utilizando O_NOFOLLOW cuando está disponible.

    Calcula SHA-256 usando el mismo descriptor físico que
    posteriormente puede ser utilizado para autorizar unlink().
    """

    esperado = (
        normalizar_sha256(
            respaldo.sha256
        )
    )


    if not esperado:

        raise RuntimeError(
            "El respaldo no tiene SHA-256 "
            "registrado por ESP013."
        )


    (
        base,
        path,
    ) = (
        _resolver_ruta_zip(
            respaldo
        )
    )


    flags_directorio = (
        os.O_RDONLY
    )


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

        flags_archivo = (
            os.O_RDONLY
        )


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


        info_antes = os.fstat(
            archivo_fd
        )


        if not statmod.S_ISREG(
            info_antes.st_mode
        ):

            raise RuntimeError(
                "El respaldo dejó de ser "
                "un archivo regular."
            )


        # ---------------------------------------------------------------------
        # Hardlinks
        # ---------------------------------------------------------------------

        enlaces = int(
            getattr(
                info_antes,
                "st_nlink",
                0,
            )
        )


        if enlaces != 1:

            raise RuntimeError(
                (
                    "El ZIP posee "
                    f"{enlaces} enlaces físicos. "
                    "ESP015 no lo retirará."
                )
            )


        tamano = int(
            info_antes.st_size
        )


        if (
            respaldo.total_bytes_paquete
            and tamano
            != respaldo.total_bytes_paquete
        ):

            raise RuntimeError(
                "El tamaño actual del ZIP "
                "no coincide con ESP013."
            )


        # ---------------------------------------------------------------------
        # SHA-256
        # ---------------------------------------------------------------------

        digest = hashlib.sha256()


        os.lseek(
            archivo_fd,
            0,
            os.SEEK_SET,
        )


        while True:

            bloque = os.read(
                archivo_fd,
                TAMANO_BLOQUE,
            )


            if not bloque:
                break


            digest.update(
                bloque
            )


        sha256 = (
            digest.hexdigest()
        )


        if sha256 != esperado:

            raise RuntimeError(
                "El SHA-256 actual del ZIP "
                "no coincide con ESP013."
            )


        # ---------------------------------------------------------------------
        # Confirmar que no cambió durante el hash.
        # ---------------------------------------------------------------------

        info_despues = os.fstat(
            archivo_fd
        )


        if (
            int(
                info_despues.st_ino
            )
            != int(
                info_antes.st_ino
            )
            or
            int(
                info_despues.st_dev
            )
            != int(
                info_antes.st_dev
            )
            or
            int(
                info_despues.st_size
            )
            != int(
                info_antes.st_size
            )
            or
            int(
                info_despues.st_mtime_ns
            )
            != int(
                info_antes.st_mtime_ns
            )
        ):

            raise RuntimeError(
                "El ZIP cambió durante "
                "la validación."
            )


        # ---------------------------------------------------------------------
        # El nombre actual debe seguir apuntando
        # al mismo inode.
        # ---------------------------------------------------------------------

        info_nombre = os.stat(
            path.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )


        if not statmod.S_ISREG(
            info_nombre.st_mode
        ):

            raise RuntimeError(
                "La ruta del ZIP dejó de apuntar "
                "a un archivo regular."
            )


        if (
            int(
                info_nombre.st_ino
            )
            != int(
                info_antes.st_ino
            )
            or
            int(
                info_nombre.st_dev
            )
            != int(
                info_antes.st_dev
            )
        ):

            raise RuntimeError(
                "La identidad física del ZIP "
                "cambió durante la validación."
            )


        yield {
            "base": base,

            "path": path,

            "parent_fd": (
                parent_fd
            ),

            "archivo_fd": (
                archivo_fd
            ),

            "stat": (
                info_antes
            ),

            "tamano": (
                tamano
            ),

            "sha256": (
                sha256
            ),

            "enlaces": (
                enlaces
            ),
        }


    finally:

        if archivo_fd is not None:

            os.close(
                archivo_fd
            )


        os.close(
            parent_fd
        )


# =============================================================================
# INSPECCIÓN SIN BORRAR
# =============================================================================


def _inspeccionar_zip(
    respaldo,
):

    with _abrir_zip_seguro(
        respaldo
    ) as datos:

        return {
            "path": (
                datos[
                    "path"
                ]
            ),

            "tamano": (
                datos[
                    "tamano"
                ]
            ),

            "sha256": (
                datos[
                    "sha256"
                ]
            ),

            "enlaces": (
                datos[
                    "enlaces"
                ]
            ),
        }


# =============================================================================
# BORRADO SEGURO DEL ZIP
# =============================================================================


def _eliminar_zip_seguro(
    respaldo,
):

    with _abrir_zip_seguro(
        respaldo
    ) as datos:

        info_original = (
            datos[
                "stat"
            ]
        )


        # ---------------------------------------------------------------------
        # Revalidación inmediatamente antes de unlink.
        # ---------------------------------------------------------------------

        info_fd = os.fstat(
            datos[
                "archivo_fd"
            ]
        )


        info_nombre = os.stat(
            datos[
                "path"
            ].name,
            dir_fd=(
                datos[
                    "parent_fd"
                ]
            ),
            follow_symlinks=False,
        )


        if (
            int(
                info_fd.st_ino
            )
            != int(
                info_original.st_ino
            )
            or
            int(
                info_fd.st_dev
            )
            != int(
                info_original.st_dev
            )
            or
            int(
                info_fd.st_size
            )
            != int(
                info_original.st_size
            )
            or
            int(
                info_fd.st_mtime_ns
            )
            != int(
                info_original.st_mtime_ns
            )
        ):

            raise RuntimeError(
                "El ZIP cambió justo antes "
                "de ser retirado."
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
                "La ruta física del ZIP cambió "
                "justo antes de ser retirada."
            )


        if int(
            getattr(
                info_nombre,
                "st_nlink",
                0,
            )
        ) != 1:

            raise RuntimeError(
                "El número de enlaces físicos "
                "del ZIP cambió."
            )


        tamano = int(
            info_fd.st_size
        )


        sha256 = (
            datos[
                "sha256"
            ]
        )


        os.unlink(
            datos[
                "path"
            ].name,
            dir_fd=(
                datos[
                    "parent_fd"
                ]
            ),
        )


        return {
            "tamano": (
                tamano
            ),

            "sha256": (
                sha256
            ),
        }


# =============================================================================
# EVALUACIÓN
# =============================================================================


def evaluar_retiro_respaldo(
    respaldo,
):

    lote = (
        respaldo.lote
    )


    resultado = {
        "respaldo": (
            respaldo
        ),

        "lote": (
            lote
        ),

        "apto": False,

        "condiciones": [],

        "liberacion": None,

        "descarga": None,

        "inspeccion": None,

        "retiro_completado": None,

        "frase_confirmacion": (
            frase_confirmacion_retiro(
                respaldo
            )
        ),
    }


    # =========================================================================
    # YA RETIRADO
    # =========================================================================

    retiro_completado = (
        respaldo.retiros_servidor
        .filter(
            estado=(
                RetiroRespaldoServidor
                .Estado
                .COMPLETADO
            )
        )
        .order_by(
            "-finalizado_en",
            "-id",
        )
        .first()
    )


    resultado[
        "retiro_completado"
    ] = retiro_completado


    no_retirado = (
        retiro_completado is None
    )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "NO_RETIRADO",
            "ZIP todavía no retirado",
            no_retirado,
            (
                "No existe un retiro previo completado."
                if no_retirado
                else
                (
                    f"El ZIP fue retirado en "
                    f"la operación "
                    f"#{retiro_completado.pk}."
                )
            ),
        )
    )


    # =========================================================================
    # ESTADO DEL LOTE
    # =========================================================================

    lote_liberado = (
        lote.estado
        == LoteCandidatosMantenimiento
        .Estado
        .LIBERADO
    )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "LOTE_LIBERADO",
            "Originales liberados",
            lote_liberado,
            (
                "El lote está en estado LIBERADO."
                if lote_liberado
                else
                (
                    "El lote todavía no está "
                    "completamente liberado."
                )
            ),
        )
    )


    # =========================================================================
    # RESPALDO ESP013
    # =========================================================================

    respaldo_listo = (
        respaldo.estado
        == RespaldoMantenimiento
        .Estado
        .LISTO
    )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "RESPALDO_LISTO",
            "Respaldo ESP013 completo",
            respaldo_listo,
            (
                "El respaldo permanece registrado "
                "como LISTO."
                if respaldo_listo
                else
                (
                    "El respaldo no está "
                    "en estado LISTO."
                )
            ),
        )
    )


    # =========================================================================
    # LIBERACIÓN ESP015 COMPLETADA
    # =========================================================================

    liberacion = (
        respaldo.liberaciones
        .filter(
            lote=lote,

            estado=(
                LiberacionMantenimiento
                .Estado
                .COMPLETADA
            ),
        )
        .order_by(
            "-finalizado_en",
            "-id",
        )
        .first()
    )


    resultado[
        "liberacion"
    ] = liberacion


    liberacion_ok = (
        liberacion is not None
    )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "LIBERACION_COMPLETA",
            "Liberación ESP015 completada",
            liberacion_ok,
            (
                (
                    f"Liberación "
                    f"#{liberacion.pk} "
                    "COMPLETADA."
                )
                if liberacion
                else
                (
                    "No existe una liberación "
                    "completa asociada a este respaldo."
                )
            ),
        )
    )


    # =========================================================================
    # DESCARGA VERIFICADA
    # =========================================================================

    descarga = (
        liberacion.descarga_verificada
        if liberacion
        else None
    )


    resultado[
        "descarga"
    ] = descarga


    descarga_ok = (
        descarga is not None
        and descarga.estado
        == RegistroDescargaRespaldo
        .Estado
        .VERIFICADA
        and descarga.respaldo_id
        == respaldo.pk
    )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "DESCARGA_VERIFICADA",
            "Copia descargada y verificada",
            descarga_ok,
            (
                (
                    f"Descarga "
                    f"#{descarga.pk} "
                    "verificada mediante SHA-256."
                )
                if descarga_ok
                else
                (
                    "No existe una descarga "
                    "ESP014 verificada válida."
                )
            ),
        )
    )


    # =========================================================================
    # ZIP FÍSICO
    # =========================================================================

    integridad_ok = False

    detalle_integridad = (
        "El ZIP no pudo ser validado."
    )


    if no_retirado:

        try:

            inspeccion = (
                _inspeccionar_zip(
                    respaldo
                )
            )


            resultado[
                "inspeccion"
            ] = inspeccion


            integridad_ok = True


            detalle_integridad = (
                "ZIP físico válido · "
                f"{bytes_legibles(inspeccion['tamano'])} · "
                "SHA-256 coincide con ESP013 · "
                f"hardlinks={inspeccion['enlaces']}."
            )


        except Exception as exc:

            detalle_integridad = (
                str(
                    exc
                )
            )


    resultado[
        "condiciones"
    ].append(
        _condicion(
            "ZIP_INTEGRO",
            "ZIP privado íntegro",
            integridad_ok,
            detalle_integridad,
        )
    )


    # =========================================================================
    # RESULTADO
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
# EJECUTAR
# =============================================================================


def ejecutar_retiro_respaldo(
    *,
    respaldo,
    usuario="",
    confirmacion="",
):

    resultado = {
        "retiro": None,

        "error": "",

        "estado": "",
    }


    esperada = (
        frase_confirmacion_retiro(
            respaldo
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
    # EVALUACIÓN COMPLETA
    # =========================================================================

    evaluacion = (
        evaluar_retiro_respaldo(
            respaldo
        )
    )


    if not evaluacion[
        "apto"
    ]:

        resultado[
            "error"
        ] = (
            "El respaldo ya no cumple todas "
            "las condiciones necesarias "
            "para ser retirado."
        )

        return resultado


    liberacion = (
        evaluacion[
            "liberacion"
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

        respaldo_bloqueado = (
            RespaldoMantenimiento
            .objects
            .select_for_update()
            .select_related(
                "lote"
            )
            .get(
                pk=respaldo.pk
            )
        )


        lote_bloqueado = (
            LoteCandidatosMantenimiento
            .objects
            .select_for_update()
            .get(
                pk=respaldo_bloqueado
                .lote_id
            )
        )


        if (
            lote_bloqueado.estado
            != LoteCandidatosMantenimiento
            .Estado
            .LIBERADO
        ):

            resultado[
                "error"
            ] = (
                "El lote dejó de estar "
                "en estado LIBERADO."
            )

            return resultado


        retiro_existente = (
            respaldo_bloqueado
            .retiros_servidor
            .filter(
                estado__in=[
                    (
                        RetiroRespaldoServidor
                        .Estado
                        .EJECUTANDO
                    ),
                    (
                        RetiroRespaldoServidor
                        .Estado
                        .COMPLETADO
                    ),
                ]
            )
            .exists()
        )


        if retiro_existente:

            resultado[
                "error"
            ] = (
                "Este respaldo ya posee "
                "un retiro activo o completado."
            )

            return resultado


        liberacion_actual = (
            respaldo_bloqueado
            .liberaciones
            .filter(
                lote=lote_bloqueado,

                estado=(
                    LiberacionMantenimiento
                    .Estado
                    .COMPLETADA
                ),
            )
            .order_by(
                "-finalizado_en",
                "-id",
            )
            .first()
        )


        if not liberacion_actual:

            resultado[
                "error"
            ] = (
                "Ya no existe una liberación "
                "ESP015 completa válida."
            )

            return resultado


        descarga_actual = (
            liberacion_actual
            .descarga_verificada
        )


        if (
            descarga_actual.estado
            != RegistroDescargaRespaldo
            .Estado
            .VERIFICADA
            or
            descarga_actual.respaldo_id
            != respaldo_bloqueado.pk
        ):

            resultado[
                "error"
            ] = (
                "La descarga ESP014 asociada "
                "ya no está verificada."
            )

            return resultado


        retiro = (
            RetiroRespaldoServidor
            .objects
            .create(

                respaldo=(
                    respaldo_bloqueado
                ),

                liberacion=(
                    liberacion_actual
                ),

                descarga_verificada=(
                    descarga_actual
                ),

                estado=(
                    RetiroRespaldoServidor
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

                nombre_archivo_snapshot=(
                    respaldo_bloqueado
                    .nombre_archivo
                ),

                total_bytes_snapshot=(
                    respaldo_bloqueado
                    .total_bytes_paquete
                ),

                sha256_snapshot=(
                    respaldo_bloqueado
                    .sha256
                ),

                confirmacion=(
                    confirmacion[
                        :100
                    ]
                ),

                detalle=(
                    "Retiro del ZIP privado "
                    "iniciado."
                ),
            )
        )


    resultado[
        "retiro"
    ] = retiro


    # =========================================================================
    # RETIRO FÍSICO
    # =========================================================================

    try:

        eliminado = (
            _eliminar_zip_seguro(
                respaldo
            )
        )


        retiro.estado = (
            RetiroRespaldoServidor
            .Estado
            .COMPLETADO
        )


        retiro.total_bytes_snapshot = (
            eliminado[
                "tamano"
            ]
        )


        retiro.sha256_snapshot = (
            eliminado[
                "sha256"
            ]
        )


        retiro.detalle = (
            "ZIP privado retirado del servidor "
            "después de validar su integridad "
            "SHA-256 y la existencia de una "
            "descarga ESP014 verificada."
        )


        retiro.errores = []


        retiro.finalizado_en = (
            timezone.now()
        )


        retiro.save(
            update_fields=[
                "estado",
                "total_bytes_snapshot",
                "sha256_snapshot",
                "detalle",
                "errores",
                "finalizado_en",
            ]
        )


        resultado[
            "estado"
        ] = retiro.estado


        return resultado


    except Exception as exc:

        retiro.estado = (
            RetiroRespaldoServidor
            .Estado
            .ERROR
        )


        retiro.detalle = (
            "El ZIP no pudo ser retirado."
        )


        retiro.errores = [
            str(
                exc
            )
        ]


        retiro.finalizado_en = (
            timezone.now()
        )


        retiro.save(
            update_fields=[
                "estado",
                "detalle",
                "errores",
                "finalizado_en",
            ]
        )


        resultado[
            "error"
        ] = str(
            exc
        )


        resultado[
            "estado"
        ] = retiro.estado


        return resultado