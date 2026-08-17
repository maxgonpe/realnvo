from __future__ import annotations

import hashlib
import os
import re
import secrets
import shutil
import sqlite3
import stat
import subprocess

from pathlib import Path

from django.conf import settings
from django.db import connection
from django.utils import timezone

from .models import (
    RespaldoBaseDatos,
)


# =============================================================================
# ESP020-B — RESPALDO MANUAL DE BASE DE DATOS
# =============================================================================
#
# RESPONSABILIDAD
#
# ✓ crear respaldo manual
# ✓ verificarlo
# ✓ calcular SHA-256
# ✓ registrar evidencia
# ✓ permitir descarga
#
# NO:
#
# ✗ restaura bases
# ✗ elimina respaldos
# ✗ modifica tablas observadas
# ✗ importa modelos de negocio
#
# =============================================================================


class ErrorRespaldoBaseDatos(
    Exception
):
    pass


# =============================================================================
# DIRECTORIO PRIVADO
# =============================================================================


def obtener_directorio_respaldos_bd():

    base_dir = Path(
        settings.BASE_DIR
    ).resolve()


    privado = (
        base_dir
        / ".espaciometro"
    )


    if (
        privado.exists()
        and privado.is_symlink()
    ):

        raise ErrorRespaldoBaseDatos(
            "El directorio privado "
            ".espaciometro no puede ser "
            "un enlace simbólico."
        )


    privado.mkdir(
        mode=0o700,
        parents=True,
        exist_ok=True,
    )


    try:
        os.chmod(
            privado,
            0o700,
        )
    except OSError:
        pass


    respaldos = (
        privado
        / "database_backups"
    )


    if (
        respaldos.exists()
        and respaldos.is_symlink()
    ):

        raise ErrorRespaldoBaseDatos(
            "El directorio de respaldos "
            "de base de datos no puede "
            "ser un enlace simbólico."
        )


    respaldos.mkdir(
        mode=0o700,
        parents=True,
        exist_ok=True,
    )


    try:
        os.chmod(
            respaldos,
            0o700,
        )
    except OSError:
        pass


    return respaldos


def _directorio_motor(
    vendor,
):

    raiz = (
        obtener_directorio_respaldos_bd()
    )


    nombre = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        str(
            vendor
            or "desconocido"
        ),
    )


    directorio = (
        raiz
        / nombre
    )


    if (
        directorio.exists()
        and directorio.is_symlink()
    ):

        raise ErrorRespaldoBaseDatos(
            "El directorio específico "
            "del motor no puede ser "
            "un enlace simbólico."
        )


    directorio.mkdir(
        mode=0o700,
        parents=True,
        exist_ok=True,
    )


    try:
        os.chmod(
            directorio,
            0o700,
        )
    except OSError:
        pass


    return directorio


# =============================================================================
# NOMBRES
# =============================================================================


def _nombre_seguro(
    valor,
):

    valor = str(
        valor
        or "database"
    )


    valor = re.sub(
        r"[^a-zA-Z0-9._-]+",
        "_",
        valor,
    )


    valor = valor.strip(
        "._-"
    )


    return (
        valor
        or "database"
    )


def _crear_nombre_archivo(
    *,
    nombre_base,
    extension,
):

    ahora = (
        timezone
        .localtime()
    )


    marca = ahora.strftime(
        "%Y%m%d_%H%M%S"
    )


    token = (
        secrets
        .token_hex(
            4
        )
    )


    nombre = (
        _nombre_seguro(
            nombre_base
        )
    )


    return (
        f"{nombre}_"
        f"{marca}_"
        f"{token}"
        f"{extension}"
    )


# =============================================================================
# SHA-256
# =============================================================================


def _sha256_archivo(
    path,
):

    digest = hashlib.sha256()


    with open(
        path,
        "rb",
    ) as archivo:

        while True:

            bloque = archivo.read(
                1024 * 1024
            )


            if not bloque:
                break


            digest.update(
                bloque
            )


    return digest.hexdigest()


# =============================================================================
# SQLITE
# =============================================================================


def _crear_respaldo_sqlite(
    *,
    directorio,
    nombre_base,
):

    connection.ensure_connection()


    origen = (
        connection.connection
    )


    if origen is None:

        raise ErrorRespaldoBaseDatos(
            "No existe una conexión "
            "SQLite activa."
        )


    nombre_archivo = (
        _crear_nombre_archivo(
            nombre_base=(
                Path(
                    str(
                        nombre_base
                    )
                ).stem
            ),
            extension=".sql",
        )
    )


    final_path = (
        directorio
        / nombre_archivo
    )


    temp_sql = (
        directorio
        / (
            ".tmp_"
            + nombre_archivo
        )
    )


    temp_db = (
        directorio
        / (
            ".tmp_"
            + secrets.token_hex(8)
            + ".sqlite3"
        )
    )


    verify_db = (
        directorio
        / (
            ".verify_"
            + secrets.token_hex(8)
            + ".sqlite3"
        )
    )


    try:

        # =====================================================================
        # 1. Crear una copia consistente SQLite
        # =====================================================================

        destino = sqlite3.connect(
            str(
                temp_db
            )
        )


        try:

            origen.backup(
                destino
            )

        finally:

            destino.close()


        # =====================================================================
        # 2. Generar dump SQL desde la copia consistente
        # =====================================================================

        copia = sqlite3.connect(
            str(
                temp_db
            )
        )


        try:

            fd = os.open(
                str(
                    temp_sql
                ),
                (
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                ),
                0o600,
            )


            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
                newline="\n",
            ) as salida:

                for linea in copia.iterdump():

                    salida.write(
                        linea
                    )

                    salida.write(
                        "\n"
                    )


                salida.flush()

                os.fsync(
                    salida.fileno()
                )


        finally:

            copia.close()


        # =====================================================================
        # 3. Comprobar que el dump existe y contiene datos
        # =====================================================================

        if not temp_sql.exists():

            raise ErrorRespaldoBaseDatos(
                "SQLite no generó "
                "el dump SQL."
            )


        tamano = (
            temp_sql
            .stat()
            .st_size
        )


        if tamano <= 0:

            raise ErrorRespaldoBaseDatos(
                "El dump SQLite quedó vacío."
            )


        # =====================================================================
        # 4. Verificación real: reconstruir en una BD temporal
        # =====================================================================

        verificacion = sqlite3.connect(
            str(
                verify_db
            )
        )


        try:

            contenido = (
                temp_sql
                .read_text(
                    encoding="utf-8"
                )
            )


            verificacion.executescript(
                contenido
            )


            fila = (
                verificacion
                .execute(
                    "PRAGMA integrity_check"
                )
                .fetchone()
            )


            if (
                not fila
                or str(
                    fila[0]
                ).lower()
                != "ok"
            ):

                raise ErrorRespaldoBaseDatos(
                    "El dump SQLite pudo "
                    "ejecutarse, pero "
                    "integrity_check no "
                    "devolvió OK."
                )


        finally:

            verificacion.close()


        # =====================================================================
        # 5. Publicación atómica
        # =====================================================================

        os.replace(
            temp_sql,
            final_path,
        )


        try:

            os.chmod(
                final_path,
                0o600,
            )

        except OSError:
            pass


        total_bytes = (
            final_path
            .stat()
            .st_size
        )


        sha256 = (
            _sha256_archivo(
                final_path
            )
        )


        return {
            "nombre_archivo": (
                nombre_archivo
            ),

            "path": (
                final_path
            ),

            "total_bytes": (
                total_bytes
            ),

            "sha256": (
                sha256
            ),

            "formato": (
                RespaldoBaseDatos
                .Formato
                .SQLITE_SQL
            ),

            "detalle": (
                "Dump SQL creado desde "
                "una copia consistente "
                "de SQLite y verificado "
                "mediante reconstrucción "
                "temporal e integrity_check."
            ),
        }


    finally:

        for temporal in (
            temp_sql,
            temp_db,
            verify_db,
        ):

            try:

                if temporal.exists():

                    temporal.unlink()

            except OSError:

                pass


# =============================================================================
# POSTGRESQL
# =============================================================================


def _ejecutable(
    nombre,
):

    path = shutil.which(
        nombre
    )


    if not path:

        raise ErrorRespaldoBaseDatos(
            f"No se encontró el ejecutable "
            f"'{nombre}' en el servidor."
        )


    return path


def _crear_respaldo_postgresql(
    *,
    directorio,
    nombre_base,
):

    pg_dump = (
        _ejecutable(
            "pg_dump"
        )
    )


    pg_restore = (
        _ejecutable(
            "pg_restore"
        )
    )


    nombre_archivo = (
        _crear_nombre_archivo(
            nombre_base=nombre_base,
            extension=".backup",
        )
    )


    final_path = (
        directorio
        / nombre_archivo
    )


    temp_path = (
        directorio
        / (
            ".tmp_"
            + nombre_archivo
        )
    )


    config = (
        connection
        .settings_dict
    )


    env = os.environ.copy()


    database = str(
        config.get(
            "NAME",
            "",
        )
        or ""
    )


    user = str(
        config.get(
            "USER",
            "",
        )
        or ""
    )


    password = str(
        config.get(
            "PASSWORD",
            "",
        )
        or ""
    )


    host = str(
        config.get(
            "HOST",
            "",
        )
        or ""
    )


    port = str(
        config.get(
            "PORT",
            "",
        )
        or ""
    )


    if not database:

        raise ErrorRespaldoBaseDatos(
            "Django no informa el nombre "
            "de la base PostgreSQL."
        )


    env[
        "PGDATABASE"
    ] = database


    if user:

        env[
            "PGUSER"
        ] = user


    if password:

        env[
            "PGPASSWORD"
        ] = password


    if host:

        env[
            "PGHOST"
        ] = host


    if port:

        env[
            "PGPORT"
        ] = port


    comando = [
        pg_dump,

        "--format=custom",

        "--file",
        str(
            temp_path
        ),

        "--no-password",
    ]


    try:

        proceso = subprocess.run(
            comando,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=3600,
        )


        if proceso.returncode != 0:

            error = (
                proceso.stderr
                or proceso.stdout
                or "pg_dump terminó con error."
            )


            raise ErrorRespaldoBaseDatos(
                error.strip()
            )


        if not temp_path.exists():

            raise ErrorRespaldoBaseDatos(
                "pg_dump terminó pero "
                "no creó el archivo."
            )


        if (
            temp_path
            .stat()
            .st_size
            <= 0
        ):

            raise ErrorRespaldoBaseDatos(
                "El archivo generado "
                "por pg_dump está vacío."
            )


        # =====================================================================
        # Validar el archivo sin restaurarlo
        # =====================================================================

        verificacion = subprocess.run(
            [
                pg_restore,
                "--list",
                str(
                    temp_path
                ),
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=3600,
        )


        if (
            verificacion.returncode
            != 0
        ):

            error = (
                verificacion.stderr
                or verificacion.stdout
                or "pg_restore --list "
                   "no pudo leer el respaldo."
            )


            raise ErrorRespaldoBaseDatos(
                error.strip()
            )


        if not (
            verificacion.stdout
            or ""
        ).strip():

            raise ErrorRespaldoBaseDatos(
                "pg_restore --list "
                "no devolvió contenido."
            )


        os.replace(
            temp_path,
            final_path,
        )


        try:

            os.chmod(
                final_path,
                0o600,
            )

        except OSError:
            pass


        total_bytes = (
            final_path
            .stat()
            .st_size
        )


        sha256 = (
            _sha256_archivo(
                final_path
            )
        )


        return {
            "nombre_archivo": (
                nombre_archivo
            ),

            "path": (
                final_path
            ),

            "total_bytes": (
                total_bytes
            ),

            "sha256": (
                sha256
            ),

            "formato": (
                RespaldoBaseDatos
                .Formato
                .POSTGRES_CUSTOM
            ),

            "detalle": (
                "Respaldo PostgreSQL "
                "creado mediante pg_dump "
                "en formato custom y "
                "verificado mediante "
                "pg_restore --list."
            ),
        }


    finally:

        try:

            if temp_path.exists():

                temp_path.unlink()

        except OSError:

            pass


# =============================================================================
# CREACIÓN PRINCIPAL
# =============================================================================


def crear_respaldo_base_datos(
    *,
    usuario="",
):

    connection.ensure_connection()


    vendor = str(
        connection.vendor
        or ""
    )


    nombre_base = str(
        connection
        .settings_dict
        .get(
            "NAME",
            "",
        )
        or ""
    )


    if vendor == "sqlite":

        nombre_mostrado = (
            Path(
                nombre_base
            ).name
            if nombre_base
            else "db.sqlite3"
        )

    else:

        nombre_mostrado = (
            nombre_base
            or "database"
        )


    directorio = (
        _directorio_motor(
            vendor
        )
    )


    archivo_generado = None


    try:

        if vendor == "sqlite":

            archivo_generado = (
                _crear_respaldo_sqlite(
                    directorio=directorio,
                    nombre_base=nombre_base,
                )
            )


        elif vendor == "postgresql":

            archivo_generado = (
                _crear_respaldo_postgresql(
                    directorio=directorio,
                    nombre_base=nombre_base,
                )
            )


        else:

            raise ErrorRespaldoBaseDatos(
                "ESP020-B todavía no "
                f"implementa respaldos para "
                f"el motor '{vendor}'."
            )


        raiz = (
            obtener_directorio_respaldos_bd()
        )


        ruta_relativa = (
            archivo_generado[
                "path"
            ]
            .relative_to(
                raiz
            )
            .as_posix()
        )


        try:

            respaldo = (
                RespaldoBaseDatos
                .objects
                .create(
                    motor=vendor,

                    nombre_base=(
                        nombre_mostrado
                    ),

                    formato=(
                        archivo_generado[
                            "formato"
                        ]
                    ),

                    estado=(
                        RespaldoBaseDatos
                        .Estado
                        .VERIFICADO
                    ),

                    usuario=str(
                        usuario
                        or ""
                    ),

                    nombre_archivo=(
                        archivo_generado[
                            "nombre_archivo"
                        ]
                    ),

                    ruta_relativa=(
                        ruta_relativa
                    ),

                    total_bytes=(
                        archivo_generado[
                            "total_bytes"
                        ]
                    ),

                    sha256=(
                        archivo_generado[
                            "sha256"
                        ]
                    ),

                    detalle=(
                        archivo_generado[
                            "detalle"
                        ]
                    ),

                    error="",

                    verificado_en=(
                        timezone.now()
                    ),
                )
            )


        except Exception:

            # Si no podemos registrar la evidencia,
            # tampoco dejamos un dump huérfano.

            try:

                archivo_generado[
                    "path"
                ].unlink()

            except OSError:

                pass


            raise


        return respaldo


    except Exception as exc:

        # Registrar también intentos fallidos.
        #
        # Este registro se crea DESPUÉS del intento,
        # por lo que un dump exitoso no contiene
        # dentro de sí su propio registro posterior.

        RespaldoBaseDatos.objects.create(
            motor=vendor,

            nombre_base=(
                nombre_mostrado
            ),

            formato=(
                RespaldoBaseDatos
                .Formato
                .SQLITE_SQL
                if vendor == "sqlite"
                else
                RespaldoBaseDatos
                .Formato
                .POSTGRES_CUSTOM
            ),

            estado=(
                RespaldoBaseDatos
                .Estado
                .ERROR
            ),

            usuario=str(
                usuario
                or ""
            ),

            nombre_archivo=(
                archivo_generado[
                    "nombre_archivo"
                ]
                if archivo_generado
                else ""
            ),

            ruta_relativa="",

            total_bytes=0,

            sha256="",

            detalle=(
                "El intento de respaldo "
                "no llegó al estado "
                "VERIFICADO."
            ),

            error=str(
                exc
            ),
        )


        if isinstance(
            exc,
            ErrorRespaldoBaseDatos,
        ):

            raise


        raise ErrorRespaldoBaseDatos(
            str(
                exc
            )
        ) from exc


# =============================================================================
# DESCARGA SEGURA
# =============================================================================


def _resolver_archivo_respaldo(
    respaldo,
):

    if (
        respaldo.estado
        != RespaldoBaseDatos
        .Estado
        .VERIFICADO
    ):

        raise ErrorRespaldoBaseDatos(
            "El respaldo no está "
            "en estado VERIFICADO."
        )


    relativa = Path(
        respaldo.ruta_relativa
        or ""
    )


    if (
        not respaldo.ruta_relativa
        or relativa.is_absolute()
        or ".." in relativa.parts
    ):

        raise ErrorRespaldoBaseDatos(
            "La ruta registrada "
            "del respaldo no es válida."
        )


    raiz = (
        obtener_directorio_respaldos_bd()
        .resolve()
    )


    path = (
        raiz
        / relativa
    )


    if path.is_symlink():

        raise ErrorRespaldoBaseDatos(
            "El respaldo no puede "
            "ser un enlace simbólico."
        )


    try:

        resuelto = (
            path.resolve(
                strict=True
            )
        )

    except OSError as exc:

        raise ErrorRespaldoBaseDatos(
            "El archivo físico del "
            "respaldo no existe."
        ) from exc


    try:

        resuelto.relative_to(
            raiz
        )

    except ValueError as exc:

        raise ErrorRespaldoBaseDatos(
            "El archivo está fuera "
            "del área privada."
        ) from exc


    return resuelto


def preparar_descarga_respaldo_bd(
    respaldo,
):

    path = (
        _resolver_archivo_respaldo(
            respaldo
        )
    )


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


    archivo = os.fdopen(
        fd,
        "rb",
    )


    try:

        info = os.fstat(
            archivo.fileno()
        )


        if not stat.S_ISREG(
            info.st_mode
        ):

            raise ErrorRespaldoBaseDatos(
                "El respaldo no es "
                "un archivo regular."
            )


        if (
            info.st_size
            != respaldo.total_bytes
        ):

            raise ErrorRespaldoBaseDatos(
                "El tamaño actual "
                "no coincide con "
                "el registrado."
            )


        digest = hashlib.sha256()


        while True:

            bloque = archivo.read(
                1024 * 1024
            )


            if not bloque:
                break


            digest.update(
                bloque
            )


        sha_actual = (
            digest.hexdigest()
        )


        if (
            sha_actual.lower()
            != (
                respaldo.sha256
                or ""
            ).lower()
        ):

            raise ErrorRespaldoBaseDatos(
                "El SHA-256 actual "
                "del respaldo no coincide "
                "con la evidencia registrada."
            )


        archivo.seek(
            0
        )


        return {
            "archivo": archivo,

            "nombre": (
                respaldo.nombre_archivo
            ),

            "total_bytes": (
                info.st_size
            ),

            "sha256": (
                sha_actual
            ),
        }


    except Exception:

        archivo.close()

        raise