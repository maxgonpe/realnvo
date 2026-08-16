from __future__ import annotations

import fnmatch
import os
import shutil
import socket
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import connections
from django.utils import timezone

from .models import RutaMonitoreada, bytes_legibles


# =============================================================================
# CLASIFICACIÓN DE ARCHIVOS
# =============================================================================

EXTENSIONES_IMAGEN = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
    ".svg",
    ".heic",
}

EXTENSIONES_DOCUMENTO = {
    ".doc",
    ".docx",
    ".odt",
    ".txt",
    ".rtf",
}

EXTENSIONES_PLANILLA = {
    ".xls",
    ".xlsx",
    ".ods",
    ".csv",
}

EXTENSIONES_VIDEO = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
    ".mpeg",
    ".mpg",
}

EXTENSIONES_COMPRIMIDO = {
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
}

EXTENSIONES_TEMPORAL = {
    ".tmp",
    ".temp",
    ".bak",
    ".cache",
    ".part",
    ".swp",
}


def clasificar_archivo(path: Path) -> str:
    extension = path.suffix.lower()

    if extension in EXTENSIONES_IMAGEN:
        return "imagen"

    if extension == ".pdf":
        return "pdf"

    if extension in EXTENSIONES_DOCUMENTO:
        return "documento"

    if extension in EXTENSIONES_PLANILLA:
        return "planilla"

    if extension in EXTENSIONES_VIDEO:
        return "video"

    if extension in EXTENSIONES_COMPRIMIDO:
        return "comprimido"

    if extension in EXTENSIONES_TEMPORAL:
        return "temporal"

    return "otro"


# =============================================================================
# UTILIDADES DE RUTAS
# =============================================================================

def resolver_ruta(ruta_monitoreada: RutaMonitoreada) -> Path:
    """
    Resuelve una RutaMonitoreada sin depender de ninguna otra aplicación.

    Si relativa_a_base_dir=True:
        intervenciones
    se convierte en:
        BASE_DIR / intervenciones
    """

    ruta = Path(ruta_monitoreada.ruta).expanduser()

    if ruta_monitoreada.relativa_a_base_dir:
        ruta = Path(settings.BASE_DIR) / ruta

    return ruta.resolve(strict=False)


def _coincide_patron(
    nombre: str,
    ruta_relativa: str,
    patrones: list[str],
) -> bool:
    if not patrones:
        return False

    for patron in patrones:
        if (
            fnmatch.fnmatch(nombre, patron)
            or fnmatch.fnmatch(ruta_relativa, patron)
        ):
            return True

    return False


def _archivo_incluido(
    nombre: str,
    ruta_relativa: str,
    patrones_incluir: list[str],
    patrones_excluir: list[str],
) -> bool:

    if _coincide_patron(
        nombre,
        ruta_relativa,
        patrones_excluir,
    ):
        return False

    if patrones_incluir:
        return _coincide_patron(
            nombre,
            ruta_relativa,
            patrones_incluir,
        )

    return True


# =============================================================================
# MEDICIÓN DEL DISCO
# =============================================================================

def obtener_estado_disco() -> dict:
    """
    Obtiene capacidad del filesystem donde se encuentra BASE_DIR.
    """

    base_dir = Path(settings.BASE_DIR).resolve()

    uso = shutil.disk_usage(base_dir)

    total = int(uso.total)
    usado = int(uso.used)
    libre = int(uso.free)

    porcentaje = 0.0

    if total:
        porcentaje = round((usado / total) * 100, 2)

    # Para el gauge:
    # 0%   = -90 grados
    # 50%  =   0 grados
    # 100% = +90 grados
    angulo = -90 + (porcentaje * 1.8)

    return {
        "ruta_base": str(base_dir),

        "total_bytes": total,
        "usado_bytes": usado,
        "libre_bytes": libre,

        "total_legible": bytes_legibles(total),
        "usado_legible": bytes_legibles(usado),
        "libre_legible": bytes_legibles(libre),

        "porcentaje_usado": porcentaje,
        "porcentaje_libre": round(100 - porcentaje, 2),

        "angulo_gauge": angulo,
    }


# =============================================================================
# MEDICIÓN DE UNA RUTA
# =============================================================================

def analizar_ruta(ruta_monitoreada: RutaMonitoreada) -> dict:
    """
    Escanea una ruta y devuelve información agregada.

    Importante:
    - no crea un registro por archivo;
    - no importa modelos externos;
    - no modifica archivos;
    - no elimina nada.
    """

    inicio = timezone.now()

    ruta_raiz = resolver_ruta(ruta_monitoreada)

    resultado = {
        "id": ruta_monitoreada.pk,
        "nombre": ruta_monitoreada.nombre,
        "categoria": ruta_monitoreada.get_categoria_display(),
        "categoria_codigo": ruta_monitoreada.categoria,

        "ruta_configurada": ruta_monitoreada.ruta,
        "ruta_resuelta": str(ruta_raiz),

        "existe": ruta_raiz.exists(),
        "es_directorio": ruta_raiz.is_dir(),

        "total_bytes": 0,
        "total_legible": bytes_legibles(0),

        "total_archivos": 0,
        "total_directorios": 0,
        "total_enlaces_simbolicos": 0,

        "total_imagenes": 0,
        "total_pdf": 0,
        "total_documentos": 0,
        "total_planillas": 0,
        "total_videos": 0,
        "total_comprimidos": 0,
        "total_temporales": 0,
        "total_otros": 0,

        "archivo_mas_antiguo": None,
        "archivo_mas_reciente": None,

        "archivo_mas_grande": None,
        "archivo_mas_grande_bytes": 0,
        "archivo_mas_grande_legible": bytes_legibles(0),

        "archivos_inaccesibles": 0,

        "error": "",
        "duracion_ms": 0,
    }

    if not ruta_raiz.exists():
        resultado["error"] = "La ruta no existe."
        return resultado

    if not ruta_raiz.is_dir():
        resultado["error"] = "La ruta configurada no es un directorio."
        return resultado

    fecha_antigua = None
    fecha_reciente = None

    ruta_antigua = ""
    ruta_reciente = ""

    ruta_grande = ""
    tamano_grande = 0

    stack = [ruta_raiz]

    while stack:
        directorio_actual = stack.pop()

        try:
            with os.scandir(directorio_actual) as entradas:

                for entrada in entradas:

                    try:
                        path = Path(entrada.path)

                        try:
                            relativa = str(
                                path.relative_to(ruta_raiz)
                            )
                        except ValueError:
                            relativa = str(path)

                        # -----------------------------------------------------
                        # Enlaces simbólicos
                        # -----------------------------------------------------

                        if entrada.is_symlink():
                            resultado[
                                "total_enlaces_simbolicos"
                            ] += 1

                            if not ruta_monitoreada.seguir_enlaces_simbolicos:
                                continue

                        # -----------------------------------------------------
                        # Directorios
                        # -----------------------------------------------------

                        if entrada.is_dir(
                            follow_symlinks=(
                                ruta_monitoreada.seguir_enlaces_simbolicos
                            )
                        ):

                            # Permite excluir carpetas completas.
                            if _coincide_patron(
                                entrada.name,
                                relativa,
                                ruta_monitoreada.patrones_excluir,
                            ):
                                continue

                            resultado["total_directorios"] += 1

                            if ruta_monitoreada.recursiva:
                                stack.append(path)

                            continue

                        # -----------------------------------------------------
                        # Archivos
                        # -----------------------------------------------------

                        if not entrada.is_file(
                            follow_symlinks=(
                                ruta_monitoreada.seguir_enlaces_simbolicos
                            )
                        ):
                            continue

                        if not _archivo_incluido(
                            entrada.name,
                            relativa,
                            ruta_monitoreada.patrones_incluir,
                            ruta_monitoreada.patrones_excluir,
                        ):
                            continue

                        stat = entrada.stat(
                            follow_symlinks=(
                                ruta_monitoreada.seguir_enlaces_simbolicos
                            )
                        )

                        tamano = int(stat.st_size)

                        fecha_modificacion = datetime.fromtimestamp(
                            stat.st_mtime,
                            tz=timezone.get_current_timezone(),
                        )

                        resultado["total_archivos"] += 1
                        resultado["total_bytes"] += tamano

                        # -----------------------------------------------------
                        # Clasificación
                        # -----------------------------------------------------

                        tipo = clasificar_archivo(path)

                        if tipo == "imagen":
                            resultado["total_imagenes"] += 1

                        elif tipo == "pdf":
                            resultado["total_pdf"] += 1

                        elif tipo == "documento":
                            resultado["total_documentos"] += 1

                        elif tipo == "planilla":
                            resultado["total_planillas"] += 1

                        elif tipo == "video":
                            resultado["total_videos"] += 1

                        elif tipo == "comprimido":
                            resultado["total_comprimidos"] += 1

                        elif tipo == "temporal":
                            resultado["total_temporales"] += 1

                        else:
                            resultado["total_otros"] += 1

                        # -----------------------------------------------------
                        # Archivo más antiguo
                        # -----------------------------------------------------

                        if (
                            fecha_antigua is None
                            or fecha_modificacion < fecha_antigua
                        ):
                            fecha_antigua = fecha_modificacion
                            ruta_antigua = relativa

                        # -----------------------------------------------------
                        # Archivo más reciente
                        # -----------------------------------------------------

                        if (
                            fecha_reciente is None
                            or fecha_modificacion > fecha_reciente
                        ):
                            fecha_reciente = fecha_modificacion
                            ruta_reciente = relativa

                        # -----------------------------------------------------
                        # Archivo más grande
                        # -----------------------------------------------------

                        if tamano > tamano_grande:
                            tamano_grande = tamano
                            ruta_grande = relativa

                    except (
                        PermissionError,
                        FileNotFoundError,
                        OSError,
                    ):
                        resultado["archivos_inaccesibles"] += 1

        except (
            PermissionError,
            FileNotFoundError,
            OSError,
        ):
            resultado["archivos_inaccesibles"] += 1

    resultado["total_legible"] = bytes_legibles(
        resultado["total_bytes"]
    )

    resultado["archivo_mas_antiguo"] = (
        {
            "ruta": ruta_antigua,
            "fecha": fecha_antigua,
        }
        if fecha_antigua
        else None
    )

    resultado["archivo_mas_reciente"] = (
        {
            "ruta": ruta_reciente,
            "fecha": fecha_reciente,
        }
        if fecha_reciente
        else None
    )

    resultado["archivo_mas_grande"] = ruta_grande or None
    resultado["archivo_mas_grande_bytes"] = tamano_grande
    resultado["archivo_mas_grande_legible"] = bytes_legibles(
        tamano_grande
    )

    fin = timezone.now()

    resultado["duracion_ms"] = int(
        (fin - inicio).total_seconds() * 1000
    )

    return resultado


# =============================================================================
# BASE DE DATOS
# =============================================================================

def obtener_estado_bases_datos() -> list[dict]:
    """
    Inspección básica y genérica de las conexiones Django.

    No conoce modelos de negocio.
    """

    resultados = []

    for alias in connections:
        connection = connections[alias]

        info = {
            "alias": alias,
            "vendor": "",
            "nombre": "",
            "total_tablas": None,
            "total_bytes": None,
            "total_legible": "-",
            "error": "",
        }

        try:
            connection.ensure_connection()

            info["vendor"] = connection.vendor

            nombre = connection.settings_dict.get("NAME", "")

            info["nombre"] = str(nombre)

            # -------------------------------------------------------------
            # Tablas
            # -------------------------------------------------------------

            try:
                info["total_tablas"] = len(
                    connection.introspection.table_names()
                )
            except Exception:
                info["total_tablas"] = None

            # -------------------------------------------------------------
            # SQLite
            # -------------------------------------------------------------

            if connection.vendor == "sqlite":

                ruta_db = Path(str(nombre))

                if ruta_db.exists() and ruta_db.is_file():
                    info["total_bytes"] = ruta_db.stat().st_size

            # -------------------------------------------------------------
            # PostgreSQL
            # -------------------------------------------------------------

            elif connection.vendor == "postgresql":

                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT pg_database_size(current_database())"
                        )

                        fila = cursor.fetchone()

                        if fila:
                            info["total_bytes"] = int(fila[0])

                except Exception:
                    # Si el usuario SQL no tiene permisos,
                    # el dashboard puede seguir funcionando.
                    pass

            if info["total_bytes"] is not None:
                info["total_legible"] = bytes_legibles(
                    info["total_bytes"]
                )

        except Exception as exc:
            info["error"] = str(exc)

        resultados.append(info)

    return resultados


# =============================================================================
# DASHBOARD GENERAL
# =============================================================================

def obtener_dashboard_espaciometro() -> dict:
    """
    Recolecta el estado actual.

    En esta primera etapa NO persiste mediciones.
    """

    disco = obtener_estado_disco()

    rutas = []

    rutas_configuradas = (
        RutaMonitoreada.objects
        .filter(activa=True, visible_dashboard=True)
        .order_by("nombre")
    )

    for ruta_monitoreada in rutas_configuradas:
        rutas.append(
            analizar_ruta(ruta_monitoreada)
        )

    bases_datos = obtener_estado_bases_datos()

    total_rutas_bytes = sum(
        ruta["total_bytes"]
        for ruta in rutas
    )

    total_archivos = sum(
        ruta["total_archivos"]
        for ruta in rutas
    )

    total_imagenes = sum(
        ruta["total_imagenes"]
        for ruta in rutas
    )

    total_pdf = sum(
        ruta["total_pdf"]
        for ruta in rutas
    )

    return {
        "generado_en": timezone.now(),
        "hostname": socket.gethostname(),

        "disco": disco,
        "rutas": rutas,
        "bases_datos": bases_datos,

        "resumen": {
            "total_rutas": len(rutas),

            "total_rutas_bytes": total_rutas_bytes,
            "total_rutas_legible": bytes_legibles(
                total_rutas_bytes
            ),

            "total_archivos": total_archivos,
            "total_imagenes": total_imagenes,
            "total_pdf": total_pdf,
        },
    }