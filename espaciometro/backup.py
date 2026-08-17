from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat as statmod
import tempfile
import zipfile

from pathlib import (
    Path,
    PurePosixPath,
)

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .candidates import (
    _estado_actual_candidato,
    _resolver_archivo_candidato,
)
from .models import (
    CandidatoMantenimiento,
    DetalleRespaldoMantenimiento,
    LoteCandidatosMantenimiento,
    RespaldoMantenimiento,
    bytes_legibles,
)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================


TAMANO_BLOQUE = (
    1024
    * 1024
)


MARGEN_LIBRE_MINIMO = (
    64
    * 1024
    * 1024
)


# =============================================================================
# EXCEPCIONES INTERNAS
# =============================================================================


class ArchivoNoVigenteAntesDeCopiar(
    RuntimeError
):
    pass


class ArchivoCambioDuranteRespaldo(
    RuntimeError
):
    pass


# =============================================================================
# DIRECTORIO DE RESPALDOS
# =============================================================================


def obtener_directorio_respaldos() -> Path:
    """
    Directorio privado utilizado por ESP013.

    Puede personalizarse en settings.py mediante:

        ESPACIOMETRO_BACKUP_DIR = "/otra/ruta"

    Si no existe configuración, se utiliza:

        BASE_DIR/.espaciometro/backups
    """

    configurado = getattr(
        settings,
        "ESPACIOMETRO_BACKUP_DIR",
        None,
    )


    if configurado:

        base = Path(
            configurado
        ).expanduser()

    else:

        base = (
            Path(
                settings.BASE_DIR
            )
            / ".espaciometro"
            / "backups"
        )


    if (
        base.exists()
        and base.is_symlink()
    ):

        raise RuntimeError(
            "El directorio de respaldos "
            "no puede ser un enlace simbólico."
        )


    base.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )


    if base.is_symlink():

        raise RuntimeError(
            "El directorio de respaldos "
            "no puede ser un enlace simbólico."
        )


    return base.resolve()


# =============================================================================
# HASH
# =============================================================================


def _sha256_archivo(
    path: Path,
) -> str:

    digest = hashlib.sha256()


    with path.open(
        "rb"
    ) as archivo:

        while True:

            bloque = archivo.read(
                TAMANO_BLOQUE
            )


            if not bloque:
                break


            digest.update(
                bloque
            )


    return digest.hexdigest()


# =============================================================================
# SNAPSHOT
# =============================================================================


def _stat_coincide_snapshot(
    candidato: CandidatoMantenimiento,
    stat,
) -> bool:


    if int(
        stat.st_size
    ) != int(
        candidato.total_bytes_snapshot
    ):

        return False


    if int(
        stat.st_mtime_ns
    ) != int(
        candidato.mtime_ns_snapshot
    ):

        return False


    inode = max(
        int(
            getattr(
                stat,
                "st_ino",
                0,
            )
        ),
        0,
    )


    dispositivo = max(
        int(
            getattr(
                stat,
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
# RUTA INTERNA DEL ZIP
# =============================================================================


def _ruta_zip(
    candidato: CandidatoMantenimiento,
) -> str:

    relativa = Path(
        candidato.ruta_relativa
    )


    if relativa.is_absolute():

        raise ValueError(
            "Ruta relativa inválida."
        )


    partes = []


    for parte in relativa.parts:

        if parte in {
            "",
            ".",
            "..",
        }:

            raise ValueError(
                "La ruta contiene componentes "
                "no permitidos."
            )


        partes.append(
            parte
        )


    return str(
        PurePosixPath(
            "archivos",
            (
                f"ruta_"
                f"{candidato.ruta_monitoreada_id}"
            ),
            *partes,
        )
    )


# =============================================================================
# FECHA ZIP
# =============================================================================


def _fecha_zip(
    fecha,
):

    if fecha is None:

        fecha = timezone.now()


    fecha = timezone.localtime(
        fecha
    )


    anio = min(
        max(
            fecha.year,
            1980,
        ),
        2107,
    )


    return (
        anio,
        fecha.month,
        fecha.day,
        fecha.hour,
        fecha.minute,
        fecha.second,
    )


# =============================================================================
# ABRIR SIN SEGUIR SYMLINK
# =============================================================================


def _abrir_archivo_seguro(
    path: Path,
):

    flags = os.O_RDONLY


    if hasattr(
        os,
        "O_NOFOLLOW",
    ):

        flags |= os.O_NOFOLLOW


    fd = os.open(
        str(
            path
        ),
        flags,
    )


    return os.fdopen(
        fd,
        "rb",
        closefd=True,
    )


# =============================================================================
# COPIA VERIFICADA HACIA ZIP
# =============================================================================


def _copiar_archivo_a_zip(
    *,
    zip_file: zipfile.ZipFile,
    candidato: CandidatoMantenimiento,
    path: Path,
    ruta_zip: str,
) -> dict:
    """
    Copia un archivo al ZIP calculando SHA-256.

    Se comprueba el snapshot:
    - inmediatamente después de abrir;
    - después de finalizar la lectura.

    Si cambia mientras se copia, se abortará todo
    el paquete para no producir un respaldo ambiguo.
    """

    digest = hashlib.sha256()

    total_copiado = 0


    with _abrir_archivo_seguro(
        path
    ) as origen:


        stat_antes = os.fstat(
            origen.fileno()
        )


        if not statmod.S_ISREG(
            stat_antes.st_mode
        ):

            raise ArchivoNoVigenteAntesDeCopiar(
                "La ubicación ya no es "
                "un archivo regular."
            )


        if not _stat_coincide_snapshot(
            candidato,
            stat_antes,
        ):

            raise ArchivoNoVigenteAntesDeCopiar(
                "El archivo cambió antes "
                "de comenzar la copia."
            )


        info = zipfile.ZipInfo(
            filename=ruta_zip,
            date_time=_fecha_zip(
                candidato.modificado_snapshot
            ),
        )


        info.compress_type = (
            zipfile.ZIP_DEFLATED
        )


        info.external_attr = (
            0o600
            << 16
        )


        with zip_file.open(
            info,
            mode="w",
            force_zip64=True,
        ) as destino:


            while True:

                bloque = origen.read(
                    TAMANO_BLOQUE
                )


                if not bloque:
                    break


                destino.write(
                    bloque
                )


                digest.update(
                    bloque
                )


                total_copiado += len(
                    bloque
                )


        stat_despues = os.fstat(
            origen.fileno()
        )


    if (
        not _stat_coincide_snapshot(
            candidato,
            stat_despues,
        )
        or total_copiado
        != candidato.total_bytes_snapshot
    ):

        raise ArchivoCambioDuranteRespaldo(
            (
                f"El archivo "
                f"{candidato.ruta_relativa} "
                "cambió mientras se preparaba "
                "el respaldo."
            )
        )


    return {
        "bytes": (
            total_copiado
        ),

        "sha256": (
            digest.hexdigest()
        ),
    }


# =============================================================================
# DETALLE OMITIDO
# =============================================================================


def _manifest_omitido(
    candidato,
    estado,
):

    return {
        "candidato_id": (
            candidato.pk
        ),

        "ruta_monitoreada": {
            "id": (
                candidato
                .ruta_monitoreada_id
            ),

            "nombre": (
                candidato
                .ruta_monitoreada
                .nombre
            ),

            "ruta_configurada": (
                candidato
                .ruta_monitoreada
                .ruta
            ),
        },

        "ruta_relativa": (
            candidato.ruta_relativa
        ),

        "estado": (
            estado[
                "codigo"
            ]
        ),

        "motivo": (
            estado[
                "detalle"
            ]
        ),
    }


# =============================================================================
# PREPARAR RESPALDO
# =============================================================================


def preparar_respaldo_lote(
    *,
    lote: LoteCandidatosMantenimiento,
    usuario: str = "",
) -> dict:

    resultado = {
        "respaldo": None,

        "error": "",

        "estado": "",

        "incluidos": 0,

        "omitidos": 0,
    }


    # =========================================================================
    # ESTADO DEL LOTE
    # =========================================================================

    if (
        lote.estado
        != LoteCandidatosMantenimiento
        .Estado
        .ABIERTO
    ):

        resultado[
            "error"
        ] = (
            "El lote no está abierto "
            "para preparar un nuevo respaldo."
        )

        return resultado


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


    if not candidatos:

        resultado[
            "error"
        ] = (
            "El lote no contiene candidatos."
        )

        return resultado


    respaldo = (
        RespaldoMantenimiento.objects.create(

            lote=lote,

            estado=(
                RespaldoMantenimiento
                .Estado
                .PREPARANDO
            ),

            creado_por=(
                str(
                    usuario
                    or ""
                )[
                    :150
                ]
            ),

            total_candidatos=len(
                candidatos
            ),
        )
    )


    resultado[
        "respaldo"
    ] = respaldo


    temporal_path = None

    final_path = None

    final_creado = False


    try:

        # =====================================================================
        # REVALIDACIÓN ESP012
        # =====================================================================

        validos = []

        omitidos = []


        for candidato in candidatos:

            estado = (
                _estado_actual_candidato(
                    candidato
                )
            )


            if estado[
                "codigo"
            ] == "VIGENTE":

                validos.append(
                    candidato
                )

            else:

                omitidos.append(
                    {
                        "candidato": candidato,
                        "estado": estado,
                    }
                )


        if not validos:

            respaldo.estado = (
                RespaldoMantenimiento
                .Estado
                .ERROR
            )


            respaldo.omitidos = len(
                omitidos
            )


            respaldo.errores = [
                (
                    "Ningún candidato continúa "
                    "vigente para ser respaldado."
                )
            ]


            respaldo.finalizado_en = (
                timezone.now()
            )


            respaldo.save(
                update_fields=[
                    "estado",
                    "omitidos",
                    "errores",
                    "finalizado_en",
                ]
            )


            resultado[
                "error"
            ] = respaldo.errores[
                0
            ]


            resultado[
                "estado"
            ] = respaldo.estado


            return resultado


        # =====================================================================
        # DIRECTORIO PRIVADO
        # =====================================================================

        backup_dir = (
            obtener_directorio_respaldos()
        )


        total_estimado = sum(
            int(
                candidato
                .total_bytes_snapshot
            )
            for candidato
            in validos
        )


        uso_disco = shutil.disk_usage(
            backup_dir
        )


        necesario = (
            total_estimado
            + MARGEN_LIBRE_MINIMO
        )


        if uso_disco.free < necesario:

            raise RuntimeError(
                (
                    "No existe espacio libre suficiente "
                    "para preparar el respaldo. "
                    f"Contenido estimado: "
                    f"{bytes_legibles(total_estimado)}. "
                    f"Libre: "
                    f"{bytes_legibles(uso_disco.free)}."
                )
            )


        # =====================================================================
        # NOMBRE
        # =====================================================================

        nombre_archivo = (
            f"esp013_lote_{lote.pk}"
            f"_respaldo_{respaldo.pk}.zip"
        )


        final_path = (
            backup_dir
            / nombre_archivo
        )


        if final_path.exists():

            raise RuntimeError(
                "Ya existe un archivo físico "
                "con el nombre del respaldo."
            )


        fd_temporal, nombre_temporal = (
            tempfile.mkstemp(
                prefix=".esp013_",
                suffix=".tmp",
                dir=str(
                    backup_dir
                ),
            )
        )


        os.close(
            fd_temporal
        )


        temporal_path = Path(
            nombre_temporal
        )


        incluidos_manifest = []

        omitidos_manifest = [
            _manifest_omitido(
                item[
                    "candidato"
                ],
                item[
                    "estado"
                ],
            )
            for item in omitidos
        ]


        detalles = []


        for item in omitidos:

            candidato = item[
                "candidato"
            ]

            estado = item[
                "estado"
            ]


            detalles.append(
                {
                    "candidato": candidato,

                    "estado": (
                        DetalleRespaldoMantenimiento
                        .Estado
                        .OMITIDO
                    ),

                    "estado_validacion": (
                        estado[
                            "codigo"
                        ]
                    ),

                    "motivo": (
                        estado[
                            "detalle"
                        ]
                    ),

                    "ruta_zip": "",

                    "total_bytes": 0,

                    "sha256": "",
                }
            )


        total_contenido = 0


        # =====================================================================
        # CREAR ZIP
        # =====================================================================

        with zipfile.ZipFile(
            temporal_path,
            mode="w",
            compression=(
                zipfile.ZIP_DEFLATED
            ),
            allowZip64=True,
        ) as paquete:


            for candidato in validos:


                # -------------------------------------------------------------
                # Resolver nuevamente justo antes de copiar
                # -------------------------------------------------------------

                try:

                    (
                        path,
                        stat_actual,
                    ) = (
                        _resolver_archivo_candidato(
                            candidato
                            .ruta_monitoreada,

                            candidato
                            .ruta_relativa,
                        )
                    )

                except ValueError as exc:

                    estado = {
                        "codigo": "AUSENTE",
                        "detalle": str(
                            exc
                        ),
                    }


                    omitidos_manifest.append(
                        _manifest_omitido(
                            candidato,
                            estado,
                        )
                    )


                    detalles.append(
                        {
                            "candidato": candidato,

                            "estado": (
                                DetalleRespaldoMantenimiento
                                .Estado
                                .OMITIDO
                            ),

                            "estado_validacion": (
                                estado[
                                    "codigo"
                                ]
                            ),

                            "motivo": (
                                estado[
                                    "detalle"
                                ]
                            ),

                            "ruta_zip": "",

                            "total_bytes": 0,

                            "sha256": "",
                        }
                    )


                    continue


                if not _stat_coincide_snapshot(
                    candidato,
                    stat_actual,
                ):

                    estado = {
                        "codigo": "CAMBIADO",

                        "detalle": (
                            "El archivo cambió antes "
                            "de comenzar la copia."
                        ),
                    }


                    omitidos_manifest.append(
                        _manifest_omitido(
                            candidato,
                            estado,
                        )
                    )


                    detalles.append(
                        {
                            "candidato": candidato,

                            "estado": (
                                DetalleRespaldoMantenimiento
                                .Estado
                                .OMITIDO
                            ),

                            "estado_validacion": (
                                "CAMBIADO"
                            ),

                            "motivo": (
                                estado[
                                    "detalle"
                                ]
                            ),

                            "ruta_zip": "",

                            "total_bytes": 0,

                            "sha256": "",
                        }
                    )


                    continue


                ruta_en_zip = (
                    _ruta_zip(
                        candidato
                    )
                )


                try:

                    copia = (
                        _copiar_archivo_a_zip(

                            zip_file=paquete,

                            candidato=candidato,

                            path=path,

                            ruta_zip=(
                                ruta_en_zip
                            ),
                        )
                    )

                except ArchivoNoVigenteAntesDeCopiar as exc:

                    estado = {
                        "codigo": "CAMBIADO",
                        "detalle": str(
                            exc
                        ),
                    }


                    omitidos_manifest.append(
                        _manifest_omitido(
                            candidato,
                            estado,
                        )
                    )


                    detalles.append(
                        {
                            "candidato": candidato,

                            "estado": (
                                DetalleRespaldoMantenimiento
                                .Estado
                                .OMITIDO
                            ),

                            "estado_validacion": (
                                "CAMBIADO"
                            ),

                            "motivo": str(
                                exc
                            ),

                            "ruta_zip": "",

                            "total_bytes": 0,

                            "sha256": "",
                        }
                    )


                    continue


                total_contenido += (
                    copia[
                        "bytes"
                    ]
                )


                incluidos_manifest.append(
                    {
                        "candidato_id": (
                            candidato.pk
                        ),

                        "ruta_monitoreada": {
                            "id": (
                                candidato
                                .ruta_monitoreada_id
                            ),

                            "nombre": (
                                candidato
                                .ruta_monitoreada
                                .nombre
                            ),

                            "ruta_configurada": (
                                candidato
                                .ruta_monitoreada
                                .ruta
                            ),
                        },

                        "ruta_relativa": (
                            candidato
                            .ruta_relativa
                        ),

                        "ruta_zip": (
                            ruta_en_zip
                        ),

                        "tamano_bytes": (
                            copia[
                                "bytes"
                            ]
                        ),

                        "modificado_snapshot": (
                            candidato
                            .modificado_snapshot
                            .isoformat()
                            if candidato
                            .modificado_snapshot
                            else None
                        ),

                        "sha256": (
                            copia[
                                "sha256"
                            ]
                        ),
                    }
                )


                detalles.append(
                    {
                        "candidato": candidato,

                        "estado": (
                            DetalleRespaldoMantenimiento
                            .Estado
                            .INCLUIDO
                        ),

                        "estado_validacion": (
                            "VIGENTE"
                        ),

                        "motivo": (
                            "Archivo incluido "
                            "y verificado."
                        ),

                        "ruta_zip": (
                            ruta_en_zip
                        ),

                        "total_bytes": (
                            copia[
                                "bytes"
                            ]
                        ),

                        "sha256": (
                            copia[
                                "sha256"
                            ]
                        ),
                    }
                )


            # =================================================================
            # MANIFEST
            # =================================================================

            cantidad_incluidos = len(
                incluidos_manifest
            )


            cantidad_omitidos = len(
                omitidos_manifest
            )


            if cantidad_incluidos == 0:

                raise RuntimeError(
                    "Ningún archivo pudo incorporarse "
                    "al paquete de respaldo."
                )


            estado_final = (
                RespaldoMantenimiento
                .Estado
                .PARCIAL

                if cantidad_omitidos

                else

                RespaldoMantenimiento
                .Estado
                .LISTO
            )


            manifest = {
                "formato": (
                    "ESPACIOMETRO-ESP013"
                ),

                "version": 1,

                "creado_en": (
                    timezone.now()
                    .isoformat()
                ),

                "respaldo": {
                    "id": (
                        respaldo.pk
                    ),

                    "estado": (
                        estado_final
                    ),

                    "algoritmo_integridad": (
                        "SHA-256"
                    ),
                },

                "lote": {
                    "id": (
                        lote.pk
                    ),

                    "nombre": (
                        lote.nombre
                    ),

                    "creado_en": (
                        lote.creado_en
                        .isoformat()
                    ),

                    "total_archivos_snapshot": (
                        lote.total_archivos
                    ),

                    "total_bytes_snapshot": (
                        lote.total_bytes
                    ),
                },

                "resumen": {
                    "candidatos": len(
                        candidatos
                    ),

                    "incluidos": (
                        cantidad_incluidos
                    ),

                    "omitidos": (
                        cantidad_omitidos
                    ),

                    "bytes_incluidos": (
                        total_contenido
                    ),
                },

                "archivos_incluidos": (
                    incluidos_manifest
                ),

                "archivos_omitidos": (
                    omitidos_manifest
                ),
            }


            manifest_bytes = json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ).encode(
                "utf-8"
            )


            paquete.writestr(
                "manifest.json",
                manifest_bytes,
            )


        # =====================================================================
        # VERIFICAR ZIP COMPLETO
        # =====================================================================

        with zipfile.ZipFile(
            temporal_path,
            mode="r",
        ) as verificar:


            defectuoso = (
                verificar.testzip()
            )


            if defectuoso:

                raise RuntimeError(
                    (
                        "La verificación ZIP detectó "
                        f"un archivo defectuoso: "
                        f"{defectuoso}"
                    )
                )


        # =====================================================================
        # SHA-256 DEL PAQUETE
        # =====================================================================

        sha_paquete = (
            _sha256_archivo(
                temporal_path
            )
        )


        tamano_paquete = (
            temporal_path
            .stat()
            .st_size
        )


        # =====================================================================
        # PUBLICAR DE FORMA ATÓMICA
        # =====================================================================

        os.replace(
            temporal_path,
            final_path,
        )


        temporal_path = None

        final_creado = True


        try:

            os.chmod(
                final_path,
                0o600,
            )

        except OSError:
            pass


        # =====================================================================
        # GUARDAR AUDITORÍA EN BD
        # =====================================================================

        with transaction.atomic():


            objetos_detalle = []


            for item in detalles:

                objetos_detalle.append(
                    DetalleRespaldoMantenimiento(

                        respaldo=respaldo,

                        candidato=(
                            item[
                                "candidato"
                            ]
                        ),

                        estado=(
                            item[
                                "estado"
                            ]
                        ),

                        estado_validacion=(
                            item[
                                "estado_validacion"
                            ][
                                :30
                            ]
                        ),

                        motivo=(
                            item[
                                "motivo"
                            ]
                        ),

                        ruta_zip=(
                            item[
                                "ruta_zip"
                            ]
                        ),

                        total_bytes=(
                            item[
                                "total_bytes"
                            ]
                        ),

                        sha256=(
                            item[
                                "sha256"
                            ]
                        ),
                    )
                )


            (
                DetalleRespaldoMantenimiento
                .objects
                .bulk_create(
                    objetos_detalle
                )
            )


            respaldo.estado = (
                estado_final
            )


            respaldo.nombre_archivo = (
                nombre_archivo
            )


            respaldo.ruta_relativa_archivo = (
                nombre_archivo
            )


            respaldo.incluidos = (
                cantidad_incluidos
            )


            respaldo.omitidos = (
                cantidad_omitidos
            )


            respaldo.total_bytes_contenido = (
                total_contenido
            )


            respaldo.total_bytes_paquete = (
                tamano_paquete
            )


            respaldo.sha256 = (
                sha_paquete
            )


            respaldo.manifest = (
                manifest
            )


            respaldo.errores = []


            respaldo.finalizado_en = (
                timezone.now()
            )


            respaldo.save()


            # Solo un respaldo completo permite
            # declarar el lote como PREPARADO.

            if (
                estado_final
                == RespaldoMantenimiento
                .Estado
                .LISTO
            ):

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
            "estado"
        ] = respaldo.estado


        resultado[
            "incluidos"
        ] = respaldo.incluidos


        resultado[
            "omitidos"
        ] = respaldo.omitidos


        return resultado


    except Exception as exc:

        # =====================================================================
        # LIMPIEZA
        # =====================================================================

        if (
            temporal_path
            and temporal_path.exists()
        ):

            try:
                temporal_path.unlink()
            except OSError:
                pass


        if (
            final_creado
            and final_path
            and final_path.exists()
        ):

            try:
                final_path.unlink()
            except OSError:
                pass


        respaldo.estado = (
            RespaldoMantenimiento
            .Estado
            .ERROR
        )


        respaldo.errores = [
            str(
                exc
            )
        ]


        respaldo.finalizado_en = (
            timezone.now()
        )


        respaldo.save(
            update_fields=[
                "estado",
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
        ] = respaldo.estado


        return resultado


# =============================================================================
# DETALLE
# =============================================================================


def obtener_detalle_respaldo(
    respaldo: RespaldoMantenimiento,
) -> dict:

    detalles = list(
        respaldo.detalles
        .select_related(
            "candidato",
            "candidato__ruta_monitoreada",
        )
        .order_by(
            "candidato__ruta_monitoreada__nombre",
            "candidato__ruta_relativa",
        )
    )


    archivo_existe = False

    archivo_path = None


    if respaldo.ruta_relativa_archivo:

        try:

            backup_dir = (
                obtener_directorio_respaldos()
            )


            candidato = (
                backup_dir
                / respaldo
                .ruta_relativa_archivo
            )


            candidato = candidato.resolve(
                strict=False
            )


            candidato.relative_to(
                backup_dir
            )


            if (
                candidato.exists()
                and candidato.is_file()
                and not candidato.is_symlink()
            ):

                archivo_existe = True

                archivo_path = (
                    candidato
                )


        except (
            RuntimeError,
            ValueError,
            OSError,
        ):

            archivo_existe = False


    return {
        "respaldo": respaldo,

        "detalles": detalles,

        "archivo_existe": (
            archivo_existe
        ),

        "archivo_path": (
            archivo_path
        ),

        "incluidos": sum(
            1
            for item in detalles
            if item.estado
            == DetalleRespaldoMantenimiento
            .Estado
            .INCLUIDO
        ),

        "omitidos": sum(
            1
            for item in detalles
            if item.estado
            == DetalleRespaldoMantenimiento
            .Estado
            .OMITIDO
        ),
    }


# =============================================================================
# LISTADO
# =============================================================================


def obtener_respaldos_recientes(
    limite: int = 50,
):

    return (
        RespaldoMantenimiento.objects
        .select_related(
            "lote"
        )
        .order_by(
            "-creado_en"
        )[
            :limite
        ]
    )