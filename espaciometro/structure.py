from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from time import perf_counter

from django.conf import settings

from .classifier import (
    CATEGORIAS,
    clasificar_archivo,
    extension_normalizada,
    nombre_categoria,
)
from .models import bytes_legibles


# =============================================================================
# ESTADÍSTICAS
# =============================================================================


def _nuevo_resumen_tipos() -> dict:
    return {
        codigo: {
            "codigo": codigo,
            "nombre": nombre,
            "cantidad": 0,
            "total_bytes": 0,
        }
        for codigo, nombre in CATEGORIAS.items()
    }


def _nuevo_resumen_extensiones() -> dict:
    return defaultdict(
        lambda: {
            "cantidad": 0,
            "total_bytes": 0,
        }
    )


def _registrar_archivo(
    *,
    path: Path,
    tamano: int,
    tipos: dict,
    extensiones: dict,
) -> None:

    categoria = clasificar_archivo(path)

    tipos[categoria]["cantidad"] += 1
    tipos[categoria]["total_bytes"] += tamano

    extension = extension_normalizada(path)

    extensiones[extension]["cantidad"] += 1
    extensiones[extension]["total_bytes"] += tamano


def _normalizar_tipos(tipos: dict) -> list[dict]:

    resultado = []

    for datos in tipos.values():

        item = dict(datos)

        item["total_legible"] = bytes_legibles(
            item["total_bytes"]
        )

        resultado.append(item)

    resultado.sort(
        key=lambda item: item["total_bytes"],
        reverse=True,
    )

    return resultado


def _normalizar_extensiones(
    extensiones: dict,
) -> list[dict]:

    resultado = []

    for extension, datos in extensiones.items():

        resultado.append(
            {
                "extension": extension,
                "cantidad": datos["cantidad"],
                "total_bytes": datos["total_bytes"],
                "total_legible": bytes_legibles(
                    datos["total_bytes"]
                ),
            }
        )

    resultado.sort(
        key=lambda item: item["total_bytes"],
        reverse=True,
    )

    return resultado


# =============================================================================
# ANÁLISIS DE DIRECTORIO
# =============================================================================


def _analizar_directorio(ruta: Path) -> dict:

    resultado = {
        "total_bytes": 0,
        "total_archivos": 0,
        "total_directorios": 0,
        "total_enlaces": 0,
        "inaccesibles": 0,
    }

    tipos = _nuevo_resumen_tipos()
    extensiones = _nuevo_resumen_extensiones()

    stack = [ruta]

    while stack:

        actual = stack.pop()

        try:

            with os.scandir(actual) as entradas:

                for entrada in entradas:

                    try:

                        if entrada.is_symlink():

                            resultado["total_enlaces"] += 1
                            continue


                        if entrada.is_dir(
                            follow_symlinks=False
                        ):

                            resultado["total_directorios"] += 1

                            stack.append(
                                Path(entrada.path)
                            )

                            continue


                        if entrada.is_file(
                            follow_symlinks=False
                        ):

                            try:

                                stat = entrada.stat(
                                    follow_symlinks=False
                                )

                                tamano = int(
                                    stat.st_size
                                )

                            except OSError:

                                resultado[
                                    "inaccesibles"
                                ] += 1

                                continue


                            resultado["total_archivos"] += 1
                            resultado["total_bytes"] += tamano

                            _registrar_archivo(
                                path=Path(entrada.path),
                                tamano=tamano,
                                tipos=tipos,
                                extensiones=extensiones,
                            )


                    except (
                        PermissionError,
                        FileNotFoundError,
                        OSError,
                    ):

                        resultado["inaccesibles"] += 1


        except (
            PermissionError,
            FileNotFoundError,
            OSError,
        ):

            resultado["inaccesibles"] += 1


    resultado["total_legible"] = bytes_legibles(
        resultado["total_bytes"]
    )

    resultado["tipos"] = _normalizar_tipos(
        tipos
    )

    resultado["extensiones"] = _normalizar_extensiones(
        extensiones
    )

    tipos_con_archivos = [
        item
        for item in resultado["tipos"]
        if item["cantidad"] > 0
    ]

    resultado["tipo_principal"] = (
        tipos_con_archivos[0]
        if tipos_con_archivos
        else None
    )

    return resultado


# =============================================================================
# ESP002 + ESP003
# =============================================================================


def analizar_estructura_proyecto() -> dict:

    inicio = perf_counter()

    base_dir = Path(
        settings.BASE_DIR
    ).expanduser().resolve(strict=False)

    tipos_globales = _nuevo_resumen_tipos()
    extensiones_globales = _nuevo_resumen_extensiones()

    resultado = {
        "base_dir": str(base_dir),
        "existe": base_dir.exists(),

        "directorios": [],
        "archivos_raiz": [],

        "total_bytes": 0,
        "total_archivos": 0,
        "total_directorios": 0,
        "total_enlaces": 0,
        "inaccesibles": 0,

        "tipos": [],
        "extensiones": [],

        "duracion_ms": 0,
        "error": "",
    }


    if not base_dir.exists():

        resultado["error"] = (
            "BASE_DIR no existe en el filesystem."
        )

        return resultado


    if not base_dir.is_dir():

        resultado["error"] = (
            "BASE_DIR no corresponde a un directorio."
        )

        return resultado


    try:

        entradas_raiz = sorted(
            list(os.scandir(base_dir)),
            key=lambda entrada: entrada.name.casefold(),
        )

    except OSError as exc:

        resultado["error"] = str(exc)

        return resultado


    for entrada in entradas_raiz:

        try:

            path = Path(entrada.path)


            # ============================================================
            # ENLACES
            # ============================================================

            if entrada.is_symlink():

                resultado["total_enlaces"] += 1
                continue


            # ============================================================
            # DIRECTORIOS
            # ============================================================

            if entrada.is_dir(
                follow_symlinks=False
            ):

                datos = _analizar_directorio(
                    path
                )

                item = {
                    "nombre": entrada.name,
                    "ruta": str(path),
                    **datos,
                }

                resultado["directorios"].append(
                    item
                )


                resultado["total_directorios"] += (
                    datos["total_directorios"] + 1
                )

                resultado["total_archivos"] += (
                    datos["total_archivos"]
                )

                resultado["total_bytes"] += (
                    datos["total_bytes"]
                )

                resultado["total_enlaces"] += (
                    datos["total_enlaces"]
                )

                resultado["inaccesibles"] += (
                    datos["inaccesibles"]
                )


                # --------------------------------------------------------
                # Sumar clasificación del directorio al total global
                # --------------------------------------------------------

                for tipo in datos["tipos"]:

                    codigo = tipo["codigo"]

                    tipos_globales[codigo][
                        "cantidad"
                    ] += tipo["cantidad"]

                    tipos_globales[codigo][
                        "total_bytes"
                    ] += tipo["total_bytes"]


                for extension in datos["extensiones"]:

                    codigo_extension = extension[
                        "extension"
                    ]

                    extensiones_globales[
                        codigo_extension
                    ]["cantidad"] += extension["cantidad"]

                    extensiones_globales[
                        codigo_extension
                    ]["total_bytes"] += extension[
                        "total_bytes"
                    ]

                continue


            # ============================================================
            # ARCHIVOS DIRECTOS EN BASE_DIR
            # ============================================================

            if entrada.is_file(
                follow_symlinks=False
            ):

                try:

                    stat = entrada.stat(
                        follow_symlinks=False
                    )

                    tamano = int(
                        stat.st_size
                    )

                except OSError:

                    tamano = 0
                    resultado["inaccesibles"] += 1


                categoria = clasificar_archivo(
                    path
                )


                resultado["archivos_raiz"].append(
                    {
                        "nombre": entrada.name,
                        "ruta": str(path),
                        "categoria": nombre_categoria(
                            categoria
                        ),
                        "total_bytes": tamano,
                        "total_legible": bytes_legibles(
                            tamano
                        ),
                    }
                )


                resultado["total_archivos"] += 1
                resultado["total_bytes"] += tamano


                _registrar_archivo(
                    path=path,
                    tamano=tamano,
                    tipos=tipos_globales,
                    extensiones=extensiones_globales,
                )


        except (
            PermissionError,
            FileNotFoundError,
            OSError,
        ):

            resultado["inaccesibles"] += 1


    resultado["directorios"].sort(
        key=lambda item: item["total_bytes"],
        reverse=True,
    )

    resultado["archivos_raiz"].sort(
        key=lambda item: item["total_bytes"],
        reverse=True,
    )


    resultado["total_legible"] = bytes_legibles(
        resultado["total_bytes"]
    )

    resultado["tipos"] = _normalizar_tipos(
        tipos_globales
    )

    resultado["extensiones"] = _normalizar_extensiones(
        extensiones_globales
    )


    resultado["duracion_ms"] = int(
        (perf_counter() - inicio) * 1000
    )

    return resultado