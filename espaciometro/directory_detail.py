from __future__ import annotations

import os

from datetime import datetime
from pathlib import Path
from time import perf_counter

from django.conf import settings
from django.utils import timezone

from .classifier import (
    CATEGORIAS,
    clasificar_archivo,
    extension_normalizada,
    nombre_categoria,
)
from .models import (
    RutaMonitoreada,
    bytes_legibles,
)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================


MAX_ARCHIVOS_DIRECTOS_MOSTRADOS = 200


# =============================================================================
# RUTAS SEGURAS
# =============================================================================


def _resolver_raiz(
    ruta_monitoreada: RutaMonitoreada,
) -> Path:
    """
    Resuelve la raíz física de una RutaMonitoreada.
    """

    ruta = Path(
        ruta_monitoreada.ruta
    ).expanduser()

    if ruta_monitoreada.relativa_a_base_dir:

        ruta = (
            Path(settings.BASE_DIR)
            / ruta
        )

    return ruta.resolve(
        strict=False
    )


def _resolver_subruta_segura(
    raiz: Path,
    subruta: str,
) -> Path:
    """
    Resuelve una subruta y garantiza que siga
    estando dentro de la RutaMonitoreada.

    Bloquea intentos como:

        ../../
        /etc
        ../../../otro/directorio

    También evita escapar mediante symlinks.
    """

    subruta = str(
        subruta or ""
    ).strip()


    if not subruta:

        return raiz


    relativa = Path(
        subruta
    )


    if relativa.is_absolute():

        raise ValueError(
            "No se permiten rutas absolutas."
        )


    objetivo = (
        raiz
        / relativa
    ).resolve(
        strict=False
    )


    try:

        objetivo.relative_to(
            raiz
        )

    except ValueError as exc:

        raise ValueError(
            "La ruta solicitada está fuera "
            "de la ruta monitorizada."
        ) from exc


    return objetivo


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
        for codigo, nombre
        in CATEGORIAS.items()
    }


def _registrar_tipo(
    resumen: dict,
    path: Path,
    tamano: int,
) -> None:

    codigo = (
        clasificar_archivo(
            path
        )
    )


    if codigo not in resumen:

        resumen[codigo] = {
            "codigo": codigo,
            "nombre": nombre_categoria(
                codigo
            ),
            "cantidad": 0,
            "total_bytes": 0,
        }


    resumen[codigo][
        "cantidad"
    ] += 1


    resumen[codigo][
        "total_bytes"
    ] += tamano


def _combinar_tipos(
    destino: dict,
    origen: dict,
) -> None:

    for codigo, datos in origen.items():

        if codigo not in destino:

            destino[codigo] = {
                "codigo": codigo,
                "nombre": datos[
                    "nombre"
                ],
                "cantidad": 0,
                "total_bytes": 0,
            }


        destino[codigo][
            "cantidad"
        ] += datos[
            "cantidad"
        ]


        destino[codigo][
            "total_bytes"
        ] += datos[
            "total_bytes"
        ]


def _normalizar_tipos(
    resumen: dict,
) -> list[dict]:

    resultado = []


    for datos in resumen.values():

        if not datos[
            "cantidad"
        ]:

            continue


        item = dict(
            datos
        )


        item[
            "total_legible"
        ] = bytes_legibles(
            item[
                "total_bytes"
            ]
        )


        resultado.append(
            item
        )


    resultado.sort(
        key=lambda item: (
            item["total_bytes"]
        ),
        reverse=True,
    )


    return resultado


# =============================================================================
# ESCANEO RECURSIVO DE UNA SUBCARPETA
# =============================================================================


def _analizar_subarbol(
    raiz: Path,
) -> dict:
    """
    Calcula recursivamente el contenido de un directorio.

    No sigue enlaces simbólicos.
    """

    resultado = {
        "total_bytes": 0,
        "total_archivos": 0,
        "total_directorios": 0,
        "total_enlaces": 0,
        "inaccesibles": 0,
        "tipos": _nuevo_resumen_tipos(),
        "archivo_mas_grande": None,
    }


    stack = [
        raiz
    ]


    while stack:

        actual = (
            stack.pop()
        )


        try:

            with os.scandir(
                actual
            ) as entradas:


                for entrada in entradas:

                    try:

                        # =====================================================
                        # SYMLINK
                        # =====================================================

                        if entrada.is_symlink():

                            resultado[
                                "total_enlaces"
                            ] += 1

                            continue


                        # =====================================================
                        # DIRECTORIO
                        # =====================================================

                        if entrada.is_dir(
                            follow_symlinks=False
                        ):

                            resultado[
                                "total_directorios"
                            ] += 1


                            stack.append(
                                Path(
                                    entrada.path
                                )
                            )


                            continue


                        # =====================================================
                        # ARCHIVO
                        # =====================================================

                        if entrada.is_file(
                            follow_symlinks=False
                        ):


                            try:

                                stat = (
                                    entrada.stat(
                                        follow_symlinks=False
                                    )
                                )


                                tamano = int(
                                    stat.st_size
                                )


                            except OSError:

                                resultado[
                                    "inaccesibles"
                                ] += 1

                                continue


                            path = Path(
                                entrada.path
                            )


                            resultado[
                                "total_archivos"
                            ] += 1


                            resultado[
                                "total_bytes"
                            ] += tamano


                            _registrar_tipo(
                                resultado[
                                    "tipos"
                                ],
                                path,
                                tamano,
                            )


                            mayor = resultado[
                                "archivo_mas_grande"
                            ]


                            if (
                                mayor is None
                                or
                                tamano
                                > mayor[
                                    "total_bytes"
                                ]
                            ):

                                resultado[
                                    "archivo_mas_grande"
                                ] = {
                                    "ruta": str(
                                        path
                                    ),
                                    "nombre": (
                                        path.name
                                    ),
                                    "total_bytes": (
                                        tamano
                                    ),
                                    "total_legible": (
                                        bytes_legibles(
                                            tamano
                                        )
                                    ),
                                }


                    except (
                        PermissionError,
                        FileNotFoundError,
                        OSError,
                    ):

                        resultado[
                            "inaccesibles"
                        ] += 1


        except (
            PermissionError,
            FileNotFoundError,
            OSError,
        ):

            resultado[
                "inaccesibles"
            ] += 1


    resultado[
        "total_legible"
    ] = bytes_legibles(
        resultado[
            "total_bytes"
        ]
    )


    return resultado


# =============================================================================
# BREADCRUMBS
# =============================================================================


def _crear_breadcrumbs(
    raiz: Path,
    actual: Path,
    nombre_raiz: str,
) -> list[dict]:

    resultado = [
        {
            "nombre": nombre_raiz,
            "subruta": "",
        }
    ]


    if actual == raiz:

        return resultado


    relativa = (
        actual.relative_to(
            raiz
        )
    )


    acumulada = Path()


    for parte in relativa.parts:

        acumulada = (
            acumulada
            / parte
        )


        resultado.append(
            {
                "nombre": parte,
                "subruta": str(
                    acumulada
                ),
            }
        )


    return resultado


# =============================================================================
# ESP008
# =============================================================================


def analizar_detalle_directorio(
    ruta_monitoreada: RutaMonitoreada,
    subruta: str = "",
) -> dict:
    """
    ESP008.

    Analiza un nivel concreto dentro de una
    RutaMonitoreada.

    Devuelve:

    - resumen de la ubicación actual;
    - subdirectorios inmediatos;
    - tamaño recursivo de cada subdirectorio;
    - archivos directamente contenidos;
    - tipos de archivo;
    - breadcrumbs.

    No modifica el filesystem.
    """

    inicio = (
        perf_counter()
    )


    raiz = (
        _resolver_raiz(
            ruta_monitoreada
        )
    )


    resultado = {

        "ruta_id": (
            ruta_monitoreada.pk
        ),

        "nombre_ruta": (
            ruta_monitoreada.nombre
        ),

        "categoria": (
            ruta_monitoreada
            .get_categoria_display()
        ),

        "raiz": str(
            raiz
        ),

        "subruta": str(
            subruta or ""
        ),

        "ruta_actual": "",

        "ruta_actual_relativa": "",

        "breadcrumbs": [],

        "subdirectorios": [],

        "archivos": [],

        "tipos": [],

        "total_bytes": 0,

        "total_legible": "0 B",

        "total_archivos": 0,

        "archivos_directos": 0,

        "archivos_directos_mostrados": 0,

        "archivos_directos_ocultos": 0,

        "total_directorios": 0,

        "directorios_directos": 0,

        "total_enlaces": 0,

        "inaccesibles": 0,

        "archivo_mas_grande": None,

        "duracion_ms": 0,

        "error": "",
    }


    # =========================================================================
    # VALIDAR RAÍZ
    # =========================================================================

    if not raiz.exists():

        resultado[
            "error"
        ] = (
            "La ruta monitorizada "
            "no existe físicamente."
        )

        return resultado


    if not raiz.is_dir():

        resultado[
            "error"
        ] = (
            "La ruta monitorizada "
            "no corresponde a un directorio."
        )

        return resultado


    # =========================================================================
    # RESOLVER SUBRUTA
    # =========================================================================

    try:

        actual = (
            _resolver_subruta_segura(
                raiz,
                subruta,
            )
        )


    except ValueError as exc:

        resultado[
            "error"
        ] = str(
            exc
        )

        return resultado


    if not actual.exists():

        resultado[
            "error"
        ] = (
            "El directorio solicitado "
            "no existe."
        )

        return resultado


    if not actual.is_dir():

        resultado[
            "error"
        ] = (
            "La ubicación solicitada "
            "no es un directorio."
        )

        return resultado


    resultado[
        "ruta_actual"
    ] = str(
        actual
    )


    try:

        relativa_actual = (
            actual.relative_to(
                raiz
            )
        )


        resultado[
            "ruta_actual_relativa"
        ] = (
            str(
                relativa_actual
            )
            if str(
                relativa_actual
            ) != "."
            else ""
        )


    except ValueError:

        resultado[
            "ruta_actual_relativa"
        ] = ""


    resultado[
        "breadcrumbs"
    ] = _crear_breadcrumbs(
        raiz,
        actual,
        ruta_monitoreada.nombre,
    )


    # =========================================================================
    # ESTADÍSTICAS GENERALES
    # =========================================================================

    tipos_globales = (
        _nuevo_resumen_tipos()
    )


    archivos_directos = []

    subdirectorios = []


    # =========================================================================
    # ENTRADAS DIRECTAS
    # =========================================================================

    try:

        entradas = sorted(
            list(
                os.scandir(
                    actual
                )
            ),
            key=lambda entrada: (
                entrada.name.casefold()
            ),
        )


    except (
        PermissionError,
        FileNotFoundError,
        OSError,
    ) as exc:

        resultado[
            "error"
        ] = (
            "No fue posible leer "
            f"el directorio: {exc}"
        )

        return resultado


    for entrada in entradas:

        try:

            path = Path(
                entrada.path
            )


            # =================================================================
            # SYMLINK
            # =================================================================

            if entrada.is_symlink():

                resultado[
                    "total_enlaces"
                ] += 1

                continue


            # =================================================================
            # SUBDIRECTORIO INMEDIATO
            # =================================================================

            if entrada.is_dir(
                follow_symlinks=False
            ):

                datos = (
                    _analizar_subarbol(
                        path
                    )
                )


                try:

                    sub_relativa = str(
                        path.relative_to(
                            raiz
                        )
                    )


                except ValueError:

                    continue


                tipos_normalizados = (
                    _normalizar_tipos(
                        datos[
                            "tipos"
                        ]
                    )
                )


                tipo_principal = (
                    tipos_normalizados[0]
                    if tipos_normalizados
                    else None
                )


                subdirectorios.append(
                    {
                        "nombre": (
                            entrada.name
                        ),

                        "ruta": str(
                            path
                        ),

                        "subruta": (
                            sub_relativa
                        ),

                        "total_bytes": (
                            datos[
                                "total_bytes"
                            ]
                        ),

                        "total_legible": (
                            datos[
                                "total_legible"
                            ]
                        ),

                        "total_archivos": (
                            datos[
                                "total_archivos"
                            ]
                        ),

                        "total_directorios": (
                            datos[
                                "total_directorios"
                            ]
                        ),

                        "total_enlaces": (
                            datos[
                                "total_enlaces"
                            ]
                        ),

                        "inaccesibles": (
                            datos[
                                "inaccesibles"
                            ]
                        ),

                        "tipo_principal": (
                            tipo_principal
                        ),
                    }
                )


                resultado[
                    "total_bytes"
                ] += datos[
                    "total_bytes"
                ]


                resultado[
                    "total_archivos"
                ] += datos[
                    "total_archivos"
                ]


                resultado[
                    "total_directorios"
                ] += (
                    datos[
                        "total_directorios"
                    ]
                    + 1
                )


                resultado[
                    "total_enlaces"
                ] += datos[
                    "total_enlaces"
                ]


                resultado[
                    "inaccesibles"
                ] += datos[
                    "inaccesibles"
                ]


                _combinar_tipos(
                    tipos_globales,
                    datos[
                        "tipos"
                    ],
                )


                mayor = datos.get(
                    "archivo_mas_grande"
                )


                if mayor:

                    actual_mayor = (
                        resultado[
                            "archivo_mas_grande"
                        ]
                    )


                    if (
                        actual_mayor is None
                        or
                        mayor[
                            "total_bytes"
                        ]
                        > actual_mayor[
                            "total_bytes"
                        ]
                    ):

                        resultado[
                            "archivo_mas_grande"
                        ] = mayor


                continue


            # =================================================================
            # ARCHIVO DIRECTO
            # =================================================================

            if entrada.is_file(
                follow_symlinks=False
            ):


                try:

                    stat = (
                        entrada.stat(
                            follow_symlinks=False
                        )
                    )


                    tamano = int(
                        stat.st_size
                    )


                    modificado = (
                        datetime.fromtimestamp(
                            stat.st_mtime,
                            tz=(
                                timezone
                                .get_current_timezone()
                            ),
                        )
                    )


                except OSError:

                    resultado[
                        "inaccesibles"
                    ] += 1

                    continue


                categoria_codigo = (
                    clasificar_archivo(
                        path
                    )
                )


                archivo = {
                    "nombre": (
                        entrada.name
                    ),

                    "ruta": str(
                        path
                    ),

                    "extension": (
                        extension_normalizada(
                            path
                        )
                    ),

                    "categoria": (
                        nombre_categoria(
                            categoria_codigo
                        )
                    ),

                    "categoria_codigo": (
                        categoria_codigo
                    ),

                    "total_bytes": (
                        tamano
                    ),

                    "total_legible": (
                        bytes_legibles(
                            tamano
                        )
                    ),

                    "modificado": (
                        modificado
                    ),
                }


                archivos_directos.append(
                    archivo
                )


                resultado[
                    "total_bytes"
                ] += tamano


                resultado[
                    "total_archivos"
                ] += 1


                _registrar_tipo(
                    tipos_globales,
                    path,
                    tamano,
                )


                mayor = resultado[
                    "archivo_mas_grande"
                ]


                if (
                    mayor is None
                    or
                    tamano
                    > mayor[
                        "total_bytes"
                    ]
                ):

                    resultado[
                        "archivo_mas_grande"
                    ] = {
                        "ruta": str(
                            path
                        ),

                        "nombre": (
                            entrada.name
                        ),

                        "total_bytes": (
                            tamano
                        ),

                        "total_legible": (
                            bytes_legibles(
                                tamano
                            )
                        ),
                    }


        except (
            PermissionError,
            FileNotFoundError,
            OSError,
        ):

            resultado[
                "inaccesibles"
            ] += 1


    # =========================================================================
    # ORDEN
    # =========================================================================

    subdirectorios.sort(
        key=lambda item: (
            item[
                "total_bytes"
            ]
        ),
        reverse=True,
    )


    archivos_directos.sort(
        key=lambda item: (
            item[
                "total_bytes"
            ]
        ),
        reverse=True,
    )


    resultado[
        "subdirectorios"
    ] = subdirectorios


    resultado[
        "directorios_directos"
    ] = len(
        subdirectorios
    )


    resultado[
        "archivos_directos"
    ] = len(
        archivos_directos
    )


    resultado[
        "archivos"
    ] = (
        archivos_directos[
            :MAX_ARCHIVOS_DIRECTOS_MOSTRADOS
        ]
    )


    resultado[
        "archivos_directos_mostrados"
    ] = len(
        resultado[
            "archivos"
        ]
    )


    resultado[
        "archivos_directos_ocultos"
    ] = max(
        (
            len(
                archivos_directos
            )
            -
            MAX_ARCHIVOS_DIRECTOS_MOSTRADOS
        ),
        0,
    )


    resultado[
        "tipos"
    ] = _normalizar_tipos(
        tipos_globales
    )


    resultado[
        "total_legible"
    ] = bytes_legibles(
        resultado[
            "total_bytes"
        ]
    )


    resultado[
        "duracion_ms"
    ] = int(
        (
            perf_counter()
            - inicio
        )
        * 1000
    )


    return resultado