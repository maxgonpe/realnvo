from __future__ import annotations

import os

from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter
from urllib.parse import urlencode

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
# RANGOS DE CICLO DE VIDA
# =============================================================================


RANGOS = (
    {
        "codigo": "0_30",
        "nombre": "0–30 días",
        "descripcion": "Archivos recientes.",
        "min_dias": 0,
        "max_dias": 30,
    },
    {
        "codigo": "31_90",
        "nombre": "31–90 días",
        "descripcion": "Archivos relativamente recientes.",
        "min_dias": 31,
        "max_dias": 90,
    },
    {
        "codigo": "91_180",
        "nombre": "91–180 días",
        "descripcion": "Archivos de mediana antigüedad.",
        "min_dias": 91,
        "max_dias": 180,
    },
    {
        "codigo": "181_365",
        "nombre": "181–365 días",
        "descripcion": "Archivos cercanos a un año.",
        "min_dias": 181,
        "max_dias": 365,
    },
    {
        "codigo": "366_730",
        "nombre": "1–2 años",
        "descripcion": "Archivos con más de un año.",
        "min_dias": 366,
        "max_dias": 730,
    },
    {
        "codigo": "731_mas",
        "nombre": "Más de 2 años",
        "descripcion": "Archivos de larga antigüedad.",
        "min_dias": 731,
        "max_dias": None,
    },
)


# =============================================================================
# UTILIDADES
# =============================================================================


def _normalizar_extension(
    valor: str,
) -> str:

    valor = str(
        valor or ""
    ).strip().lower()

    if not valor:
        return ""

    if not valor.startswith("."):
        valor = "." + valor

    return valor


def _resolver_raiz(
    ruta: RutaMonitoreada,
) -> Path:

    path = Path(
        ruta.ruta
    ).expanduser()

    if ruta.relativa_a_base_dir:

        path = (
            Path(settings.BASE_DIR)
            / path
        )

    return path.resolve(
        strict=False
    )


def _porcentaje(
    parte: int,
    total: int,
) -> float:

    if not total:
        return 0.0

    return round(
        (
            parte
            / total
        )
        * 100,
        2,
    )


def _obtener_rango(
    antiguedad_dias: int,
) -> str:

    for rango in RANGOS:

        minimo = rango[
            "min_dias"
        ]

        maximo = rango[
            "max_dias"
        ]

        if (
            antiguedad_dias >= minimo
            and (
                maximo is None
                or antiguedad_dias <= maximo
            )
        ):

            return rango[
                "codigo"
            ]

    return "731_mas"


def _filtros_desde_params(
    params,
) -> dict:

    ruta = str(
        params.get(
            "ruta",
            "",
        )
        or ""
    ).strip()

    tipo = str(
        params.get(
            "tipo",
            "",
        )
        or ""
    ).strip()

    if tipo not in CATEGORIAS:
        tipo = ""

    extension = _normalizar_extension(
        params.get(
            "extension",
            "",
        )
    )

    return {
        "ruta": ruta,
        "tipo": tipo,
        "extension": extension,
    }


# =============================================================================
# ENLACE HACIA ESP010
# =============================================================================


def _query_inventario_rango(
    *,
    filtros: dict,
    min_dias: int,
    max_dias: int | None,
) -> str:
    """
    Genera los filtros necesarios para abrir ESP010
    con aproximadamente el mismo rango temporal.

    ESP010 trabaja con fechas calendario.
    """

    hoy = timezone.localdate()

    query = {
        "buscar": "1",
        "orden": "antiguos",
    }


    if filtros["ruta"]:
        query["ruta"] = filtros["ruta"]

    if filtros["tipo"]:
        query["tipo"] = filtros["tipo"]

    if filtros["extension"]:
        query["extension"] = filtros[
            "extension"
        ]


    # -------------------------------------------------------------------------
    # Límite más reciente del intervalo
    # -------------------------------------------------------------------------

    if min_dias > 0:

        fecha_hasta = (
            hoy
            - timedelta(
                days=min_dias
            )
        )

        query[
            "fecha_hasta"
        ] = fecha_hasta.isoformat()


    # -------------------------------------------------------------------------
    # Límite más antiguo del intervalo
    # -------------------------------------------------------------------------

    if max_dias is not None:

        fecha_desde = (
            hoy
            - timedelta(
                days=max_dias
            )
        )

        query[
            "fecha_desde"
        ] = fecha_desde.isoformat()


    return urlencode(
        query
    )


# =============================================================================
# CONFIGURACIÓN DE LA PANTALLA
# =============================================================================


def obtener_configuracion_ciclo_vida(
    params=None,
) -> dict:

    params = params or {}

    rutas = list(
        RutaMonitoreada.objects
        .filter(
            activa=True
        )
        .order_by(
            "nombre"
        )
    )

    return {
        "rutas": rutas,

        "categorias": list(
            CATEGORIAS.items()
        ),

        "filtros": (
            _filtros_desde_params(
                params
            )
        ),
    }


# =============================================================================
# ESP011
# =============================================================================


def analizar_ciclo_vida(
    params,
) -> dict:
    """
    ESP011.

    Analiza la antigüedad de los archivos actuales.

    Exclusivamente lectura.

    No:
    - mueve archivos;
    - elimina archivos;
    - modifica archivos;
    - sigue enlaces simbólicos;
    - crea operaciones de mantenimiento.
    """

    inicio = perf_counter()

    filtros = (
        _filtros_desde_params(
            params
        )
    )

    ahora = timezone.now()

    resultado = {
        "ejecutado": True,

        "filtros": filtros,

        "total_archivos": 0,

        "total_bytes": 0,

        "total_legible": "0 B",

        "archivos_antiguos": 0,

        "bytes_antiguos": 0,

        "antiguos_legible": "0 B",

        "porcentaje_antiguo": 0.0,

        "archivo_mas_antiguo": None,

        "antiguedad_maxima_dias": 0,

        "rutas_analizadas": 0,

        "archivos_examinados": 0,

        "directorios_examinados": 0,

        "enlaces_omitidos": 0,

        "inaccesibles": 0,

        "fechas_futuras": 0,

        "errores": [],

        "rangos": [],

        "rutas": [],

        "tipos": [],

        "duracion_ms": 0,

        "error": "",
    }


    # =========================================================================
    # RUTAS
    # =========================================================================

    rutas_qs = (
        RutaMonitoreada.objects
        .filter(
            activa=True
        )
        .order_by(
            "nombre"
        )
    )


    if filtros["ruta"]:

        try:

            ruta_id = int(
                filtros["ruta"]
            )

        except (
            TypeError,
            ValueError,
        ):

            resultado[
                "error"
            ] = (
                "La ruta seleccionada "
                "no es válida."
            )

            return resultado


        rutas_qs = rutas_qs.filter(
            pk=ruta_id
        )


        if not rutas_qs.exists():

            resultado[
                "error"
            ] = (
                "La ruta seleccionada "
                "no existe o no está activa."
            )

            return resultado


    rutas = list(
        rutas_qs
    )


    # =========================================================================
    # CONTADORES DE RANGOS
    # =========================================================================

    rangos = {}

    for rango in RANGOS:

        rangos[
            rango["codigo"]
        ] = {
            **rango,

            "archivos": 0,

            "total_bytes": 0,

            "total_legible": "0 B",

            "porcentaje_archivos": 0.0,

            "porcentaje_espacio": 0.0,

            "inventario_query": "",
        }


    # =========================================================================
    # RESÚMENES
    # =========================================================================

    resumen_rutas = {}

    resumen_tipos = defaultdict(
        lambda: {
            "archivos": 0,
            "total_bytes": 0,
            "archivos_antiguos": 0,
            "bytes_antiguos": 0,
        }
    )


    # Evitar doble conteo si existen rutas monitorizadas solapadas.

    paths_vistos = set()


    # =========================================================================
    # ESCANEO
    # =========================================================================

    for ruta in rutas:

        raiz = (
            _resolver_raiz(
                ruta
            )
        )


        if not raiz.exists():

            resultado[
                "errores"
            ].append(
                {
                    "ruta": ruta.nombre,

                    "detalle": (
                        "La ruta física "
                        "no existe."
                    ),
                }
            )

            continue


        if not raiz.is_dir():

            resultado[
                "errores"
            ].append(
                {
                    "ruta": ruta.nombre,

                    "detalle": (
                        "La ruta configurada "
                        "no es un directorio."
                    ),
                }
            )

            continue


        resultado[
            "rutas_analizadas"
        ] += 1


        resumen_ruta = {
            "id": ruta.pk,

            "nombre": ruta.nombre,

            "ruta": ruta.ruta,

            "archivos": 0,

            "total_bytes": 0,

            "total_legible": "0 B",

            "archivos_antiguos": 0,

            "bytes_antiguos": 0,

            "antiguos_legible": "0 B",

            "porcentaje_antiguo": 0.0,

            "archivo_mas_antiguo": None,
        }


        resumen_rutas[
            ruta.pk
        ] = resumen_ruta


        stack = [
            raiz
        ]


        while stack:

            directorio = stack.pop()

            resultado[
                "directorios_examinados"
            ] += 1


            try:

                with os.scandir(
                    directorio
                ) as entradas:


                    for entrada in entradas:


                        try:

                            # =================================================
                            # ENLACE SIMBÓLICO
                            # =================================================

                            if entrada.is_symlink():

                                resultado[
                                    "enlaces_omitidos"
                                ] += 1

                                continue


                            # =================================================
                            # DIRECTORIO
                            # =================================================

                            if entrada.is_dir(
                                follow_symlinks=False
                            ):

                                stack.append(
                                    Path(
                                        entrada.path
                                    )
                                )

                                continue


                            # =================================================
                            # ARCHIVO
                            # =================================================

                            if not entrada.is_file(
                                follow_symlinks=False
                            ):

                                continue


                            resultado[
                                "archivos_examinados"
                            ] += 1


                            path = Path(
                                entrada.path
                            )


                            path_clave = os.path.normcase(
                                os.path.abspath(
                                    str(
                                        path
                                    )
                                )
                            )


                            if (
                                path_clave
                                in paths_vistos
                            ):

                                continue


                            paths_vistos.add(
                                path_clave
                            )


                            try:

                                stat = entrada.stat(
                                    follow_symlinks=False
                                )

                            except OSError:

                                resultado[
                                    "inaccesibles"
                                ] += 1

                                continue


                            tamano = int(
                                stat.st_size
                            )


                            modificado = datetime.fromtimestamp(
                                stat.st_mtime,
                                tz=(
                                    timezone
                                    .get_current_timezone()
                                ),
                            )


                            categoria = (
                                clasificar_archivo(
                                    path
                                )
                            )


                            extension = (
                                extension_normalizada(
                                    path
                                )
                            )


                            # =================================================
                            # FILTROS
                            # =================================================

                            if (
                                filtros["tipo"]
                                and categoria
                                != filtros["tipo"]
                            ):

                                continue


                            if (
                                filtros["extension"]
                                and extension
                                != filtros["extension"]
                            ):

                                continue


                            # =================================================
                            # ANTIGÜEDAD
                            # =================================================

                            diferencia = (
                                ahora
                                - modificado
                            )


                            segundos = (
                                diferencia
                                .total_seconds()
                            )


                            if segundos < 0:

                                resultado[
                                    "fechas_futuras"
                                ] += 1

                                antiguedad_dias = 0

                            else:

                                antiguedad_dias = int(
                                    segundos
                                    // 86400
                                )


                            codigo_rango = (
                                _obtener_rango(
                                    antiguedad_dias
                                )
                            )


                            # =================================================
                            # TOTALES
                            # =================================================

                            resultado[
                                "total_archivos"
                            ] += 1


                            resultado[
                                "total_bytes"
                            ] += tamano


                            rangos[
                                codigo_rango
                            ][
                                "archivos"
                            ] += 1


                            rangos[
                                codigo_rango
                            ][
                                "total_bytes"
                            ] += tamano


                            # =================================================
                            # RUTA
                            # =================================================

                            resumen_ruta[
                                "archivos"
                            ] += 1


                            resumen_ruta[
                                "total_bytes"
                            ] += tamano


                            # =================================================
                            # TIPO
                            # =================================================

                            resumen_tipo = (
                                resumen_tipos[
                                    categoria
                                ]
                            )


                            resumen_tipo[
                                "archivos"
                            ] += 1


                            resumen_tipo[
                                "total_bytes"
                            ] += tamano


                            # =================================================
                            # MÁS DE UN AÑO
                            # =================================================

                            if antiguedad_dias >= 366:

                                resultado[
                                    "archivos_antiguos"
                                ] += 1


                                resultado[
                                    "bytes_antiguos"
                                ] += tamano


                                resumen_ruta[
                                    "archivos_antiguos"
                                ] += 1


                                resumen_ruta[
                                    "bytes_antiguos"
                                ] += tamano


                                resumen_tipo[
                                    "archivos_antiguos"
                                ] += 1


                                resumen_tipo[
                                    "bytes_antiguos"
                                ] += tamano


                            # =================================================
                            # ARCHIVO MÁS ANTIGUO GLOBAL
                            # =================================================

                            actual_antiguo = (
                                resultado[
                                    "archivo_mas_antiguo"
                                ]
                            )


                            item_antiguo = {
                                "nombre": path.name,

                                "ruta_nombre": (
                                    ruta.nombre
                                ),

                                "ruta_relativa": str(
                                    path.relative_to(
                                        raiz
                                    )
                                ),

                                "ruta_absoluta": str(
                                    path
                                ),

                                "modificado": (
                                    modificado
                                ),

                                "antiguedad_dias": (
                                    antiguedad_dias
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


                            if (
                                actual_antiguo is None
                                or modificado
                                < actual_antiguo[
                                    "modificado"
                                ]
                            ):

                                resultado[
                                    "archivo_mas_antiguo"
                                ] = item_antiguo


                            # =================================================
                            # ARCHIVO MÁS ANTIGUO DE LA RUTA
                            # =================================================

                            antiguo_ruta = (
                                resumen_ruta[
                                    "archivo_mas_antiguo"
                                ]
                            )


                            if (
                                antiguo_ruta is None
                                or modificado
                                < antiguo_ruta[
                                    "modificado"
                                ]
                            ):

                                resumen_ruta[
                                    "archivo_mas_antiguo"
                                ] = (
                                    item_antiguo
                                )


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
            ) as exc:

                resultado[
                    "inaccesibles"
                ] += 1


                resultado[
                    "errores"
                ].append(
                    {
                        "ruta": str(
                            directorio
                        ),

                        "detalle": str(
                            exc
                        ),
                    }
                )


    # =========================================================================
    # FINALIZAR RANGOS
    # =========================================================================

    rangos_resultado = []


    for rango_base in RANGOS:

        item = rangos[
            rango_base[
                "codigo"
            ]
        ]


        item[
            "total_legible"
        ] = bytes_legibles(
            item[
                "total_bytes"
            ]
        )


        item[
            "porcentaje_archivos"
        ] = _porcentaje(
            item[
                "archivos"
            ],
            resultado[
                "total_archivos"
            ],
        )


        item[
            "porcentaje_espacio"
        ] = _porcentaje(
            item[
                "total_bytes"
            ],
            resultado[
                "total_bytes"
            ],
        )


        item[
            "inventario_query"
        ] = _query_inventario_rango(

            filtros=filtros,

            min_dias=(
                item[
                    "min_dias"
                ]
            ),

            max_dias=(
                item[
                    "max_dias"
                ]
            ),
        )


        rangos_resultado.append(
            item
        )


    resultado[
        "rangos"
    ] = rangos_resultado


    # =========================================================================
    # FINALIZAR RUTAS
    # =========================================================================

    rutas_resultado = []


    for item in resumen_rutas.values():

        item[
            "total_legible"
        ] = bytes_legibles(
            item[
                "total_bytes"
            ]
        )


        item[
            "antiguos_legible"
        ] = bytes_legibles(
            item[
                "bytes_antiguos"
            ]
        )


        item[
            "porcentaje_antiguo"
        ] = _porcentaje(
            item[
                "bytes_antiguos"
            ],
            item[
                "total_bytes"
            ],
        )


        rutas_resultado.append(
            item
        )


    rutas_resultado.sort(
        key=lambda item: (
            item[
                "bytes_antiguos"
            ],
            item[
                "total_bytes"
            ],
        ),
        reverse=True,
    )


    resultado[
        "rutas"
    ] = rutas_resultado


    # =========================================================================
    # FINALIZAR TIPOS
    # =========================================================================

    tipos_resultado = []


    for codigo, datos in resumen_tipos.items():

        item = {
            "codigo": codigo,

            "nombre": (
                nombre_categoria(
                    codigo
                )
            ),

            **datos,
        }


        item[
            "total_legible"
        ] = bytes_legibles(
            item[
                "total_bytes"
            ]
        )


        item[
            "antiguos_legible"
        ] = bytes_legibles(
            item[
                "bytes_antiguos"
            ]
        )


        item[
            "porcentaje_antiguo"
        ] = _porcentaje(
            item[
                "bytes_antiguos"
            ],
            item[
                "total_bytes"
            ],
        )


        tipos_resultado.append(
            item
        )


    tipos_resultado.sort(
        key=lambda item: (
            item[
                "bytes_antiguos"
            ],
            item[
                "total_bytes"
            ],
        ),
        reverse=True,
    )


    resultado[
        "tipos"
    ] = tipos_resultado


    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================

    resultado[
        "total_legible"
    ] = bytes_legibles(
        resultado[
            "total_bytes"
        ]
    )


    resultado[
        "antiguos_legible"
    ] = bytes_legibles(
        resultado[
            "bytes_antiguos"
        ]
    )


    resultado[
        "porcentaje_antiguo"
    ] = _porcentaje(
        resultado[
            "bytes_antiguos"
        ],
        resultado[
            "total_bytes"
        ],
    )


    if resultado[
        "archivo_mas_antiguo"
    ]:

        resultado[
            "antiguedad_maxima_dias"
        ] = (
            resultado[
                "archivo_mas_antiguo"
            ][
                "antiguedad_dias"
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