from __future__ import annotations

import platform
import socket
from pathlib import Path

from django.db import connections
from django.utils import timezone

from .models import (
    EjecucionMedicion,
    MedicionBaseDatos,
    MedicionDisco,
    MedicionRuta,
    RutaMonitoreada,
)
from .services import (
    analizar_ruta,
    obtener_estado_bases_datos,
    obtener_estado_disco,
)


# =============================================================================
# UTILIDADES
# =============================================================================


def _resolver_punto_montaje(ruta: str | Path) -> str:
    """
    Intenta determinar el punto de montaje del filesystem que contiene
    la ruta suministrada.

    No requiere dependencias externas como psutil.
    """

    try:
        actual = Path(ruta).resolve()

        dispositivo = actual.stat().st_dev

        while actual.parent != actual:
            padre = actual.parent

            try:
                if padre.stat().st_dev != dispositivo:
                    break
            except OSError:
                break

            actual = padre

        return str(actual)

    except (OSError, RuntimeError, ValueError):
        return str(ruta)


# =============================================================================
# DISCO
# =============================================================================


def _guardar_medicion_disco(
    ejecucion: EjecucionMedicion,
) -> MedicionDisco:
    """
    Obtiene el estado actual del filesystem donde vive BASE_DIR
    y lo guarda como snapshot.
    """

    datos = obtener_estado_disco()

    punto_montaje = _resolver_punto_montaje(
        datos["ruta_base"]
    )

    return MedicionDisco.objects.create(
        ejecucion=ejecucion,

        punto_montaje=punto_montaje,

        total_bytes=datos["total_bytes"],
        usados_bytes=datos["usado_bytes"],
        libres_bytes=datos["libre_bytes"],
    )


# =============================================================================
# RUTAS
# =============================================================================


def _guardar_medicion_ruta(
    *,
    ejecucion: EjecucionMedicion,
    ruta_monitoreada: RutaMonitoreada,
) -> MedicionRuta:
    """
    Ejecuta el scanner existente sobre una RutaMonitoreada
    y persiste el resultado agregado.
    """

    datos = analizar_ruta(
        ruta_monitoreada
    )

    antiguo = datos.get(
        "archivo_mas_antiguo"
    )

    reciente = datos.get(
        "archivo_mas_reciente"
    )

    return MedicionRuta.objects.create(
        ejecucion=ejecucion,

        ruta_monitoreada=ruta_monitoreada,

        ruta_resuelta=datos.get(
            "ruta_resuelta",
            "",
        ),

        total_bytes=datos.get(
            "total_bytes",
            0,
        ),

        total_archivos=datos.get(
            "total_archivos",
            0,
        ),

        total_directorios=datos.get(
            "total_directorios",
            0,
        ),

        total_enlaces_simbolicos=datos.get(
            "total_enlaces_simbolicos",
            0,
        ),

        total_imagenes=datos.get(
            "total_imagenes",
            0,
        ),

        total_pdf=datos.get(
            "total_pdf",
            0,
        ),

        total_documentos=datos.get(
            "total_documentos",
            0,
        ),

        total_planillas=datos.get(
            "total_planillas",
            0,
        ),

        total_videos=datos.get(
            "total_videos",
            0,
        ),

        total_comprimidos=datos.get(
            "total_comprimidos",
            0,
        ),

        total_temporales=datos.get(
            "total_temporales",
            0,
        ),

        total_otros=datos.get(
            "total_otros",
            0,
        ),

        archivo_mas_antiguo_fecha=(
            antiguo.get("fecha")
            if antiguo
            else None
        ),

        archivo_mas_antiguo_ruta=(
            antiguo.get("ruta", "")
            if antiguo
            else ""
        ),

        archivo_mas_reciente_fecha=(
            reciente.get("fecha")
            if reciente
            else None
        ),

        archivo_mas_reciente_ruta=(
            reciente.get("ruta", "")
            if reciente
            else ""
        ),

        archivo_mas_grande_bytes=datos.get(
            "archivo_mas_grande_bytes",
            0,
        ),

        archivo_mas_grande_ruta=(
            datos.get(
                "archivo_mas_grande",
                "",
            )
            or ""
        ),

        archivos_inaccesibles=datos.get(
            "archivos_inaccesibles",
            0,
        ),

        duracion_ms=datos.get(
            "duracion_ms",
            0,
        ),

        error=datos.get(
            "error",
            "",
        ),
    )


# =============================================================================
# BASE DE DATOS
# =============================================================================


def _guardar_medicion_base_datos(
    *,
    ejecucion: EjecucionMedicion,
    datos: dict,
) -> MedicionBaseDatos:
    """
    Persiste la información general de una conexión Django.

    No almacena contraseñas.
    """

    alias = datos.get(
        "alias",
        "default",
    )

    configuracion = {}

    try:
        configuracion = connections[
            alias
        ].settings_dict
    except Exception:
        pass

    total_tablas = datos.get(
        "total_tablas"
    )

    return MedicionBaseDatos.objects.create(
        ejecucion=ejecucion,

        alias=alias,

        vendor=datos.get(
            "vendor",
            "",
        ),

        engine=str(
            configuracion.get(
                "ENGINE",
                "",
            )
            or ""
        ),

        nombre_base_datos=str(
            datos.get(
                "nombre",
                "",
            )
            or ""
        ),

        host=str(
            configuracion.get(
                "HOST",
                "",
            )
            or ""
        ),

        puerto=str(
            configuracion.get(
                "PORT",
                "",
            )
            or ""
        ),

        total_bytes=datos.get(
            "total_bytes"
        ),

        total_tablas=(
            int(total_tablas)
            if total_tablas is not None
            else 0
        ),

        # ESP020 profundizará posteriormente
        # en el conteo por tabla.
        total_registros=None,

        error=datos.get(
            "error",
            "",
        ),
    )


# =============================================================================
# MOTOR PRINCIPAL — ESP004
# =============================================================================


def ejecutar_medicion_completa() -> EjecucionMedicion:
    """
    Ejecuta una fotografía formal del estado actual del sistema.

    Esta función:

    1. crea EjecucionMedicion;
    2. mide filesystem;
    3. mide las RutaMonitoreada activas;
    4. mide las bases de datos configuradas;
    5. registra errores;
    6. cierra la ejecución.

    Una falla parcial NO elimina los resultados que sí pudieron obtenerse.
    """

    ejecucion = EjecucionMedicion.objects.create(
        iniciada_en=timezone.now(),

        estado=(
            EjecucionMedicion.Estado.EN_CURSO
        ),

        hostname=socket.gethostname(),

        plataforma=platform.platform(),

        version_python=platform.python_version(),
    )

    errores: list[str] = []

    componentes_correctos = 0

    componentes_fallidos = 0

    # =========================================================================
    # 1. DISCO
    # =========================================================================

    try:
        _guardar_medicion_disco(
            ejecucion
        )

        componentes_correctos += 1

    except Exception as exc:
        componentes_fallidos += 1

        errores.append(
            f"DISCO: {type(exc).__name__}: {exc}"
        )

    # =========================================================================
    # 2. RUTAS MONITORIZADAS
    # =========================================================================

    rutas = (
        RutaMonitoreada.objects
        .filter(activa=True)
        .order_by("nombre")
    )

    for ruta in rutas:

        try:
            medicion = _guardar_medicion_ruta(
                ejecucion=ejecucion,
                ruta_monitoreada=ruta,
            )

            componentes_correctos += 1

            if medicion.error:
                componentes_fallidos += 1

                errores.append(
                    f"RUTA {ruta.nombre}: "
                    f"{medicion.error}"
                )

        except Exception as exc:
            componentes_fallidos += 1

            errores.append(
                f"RUTA {ruta.nombre}: "
                f"{type(exc).__name__}: {exc}"
            )

    # =========================================================================
    # 3. BASES DE DATOS
    # =========================================================================

    try:
        bases_datos = (
            obtener_estado_bases_datos()
        )

    except Exception as exc:
        bases_datos = []

        componentes_fallidos += 1

        errores.append(
            "BASES DE DATOS: "
            f"{type(exc).__name__}: {exc}"
        )

    for datos_bd in bases_datos:

        alias = datos_bd.get(
            "alias",
            "default",
        )

        try:
            medicion_bd = (
                _guardar_medicion_base_datos(
                    ejecucion=ejecucion,
                    datos=datos_bd,
                )
            )

            componentes_correctos += 1

            if medicion_bd.error:
                componentes_fallidos += 1

                errores.append(
                    f"BD {alias}: "
                    f"{medicion_bd.error}"
                )

        except Exception as exc:
            componentes_fallidos += 1

            errores.append(
                f"BD {alias}: "
                f"{type(exc).__name__}: {exc}"
            )

    # =========================================================================
    # 4. ESTADO FINAL
    # =========================================================================

    if componentes_fallidos == 0:

        estado_final = (
            EjecucionMedicion.Estado.COMPLETADA
        )

    elif componentes_correctos > 0:

        estado_final = (
            EjecucionMedicion.Estado.PARCIAL
        )

    else:

        estado_final = (
            EjecucionMedicion.Estado.ERROR
        )

    ejecucion.estado = estado_final

    ejecucion.finalizada_en = timezone.now()

    ejecucion.errores = errores

    ejecucion.observaciones = (
        f"Componentes correctos: "
        f"{componentes_correctos}. "
        f"Componentes con error: "
        f"{componentes_fallidos}."
    )

    ejecucion.save(
        update_fields=[
            "estado",
            "finalizada_en",
            "errores",
            "observaciones",
        ]
    )

    return ejecucion