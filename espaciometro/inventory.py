from __future__ import annotations

import os

from datetime import (
    datetime,
    time,
)
from decimal import (
    Decimal,
    InvalidOperation,
)
from pathlib import Path
from time import perf_counter

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_date

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


MAX_RESULTADOS_MOSTRADOS = 500

# Protección de memoria.
#
# Seguimos contando TODOS los archivos coincidentes aunque
# una búsqueda extraordinariamente grande supere este límite.
#
# Solamente dejamos de conservar cada fila individual en memoria.
MAX_COINCIDENCIAS_EN_MEMORIA = 200000


UNIDADES = (
    ("KB", "KB"),
    ("MB", "MB"),
    ("GB", "GB"),
)


ORDENES = (
    (
        "tamano_desc",
        "Mayor tamaño primero",
    ),
    (
        "tamano_asc",
        "Menor tamaño primero",
    ),
    (
        "antiguos",
        "Más antiguos primero",
    ),
    (
        "recientes",
        "Más recientes primero",
    ),
    (
        "nombre",
        "Nombre / ruta",
    ),
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


def _tamano_a_bytes(
    valor: str,
    unidad: str,
) -> int | None:

    valor = str(
        valor or ""
    ).strip()


    if not valor:
        return None


    try:

        numero = Decimal(
            valor.replace(
                ",",
                ".",
            )
        )

    except (
        InvalidOperation,
        ValueError,
    ):

        raise ValueError(
            f"Tamaño no válido: {valor}"
        )


    if numero < 0:

        raise ValueError(
            "El tamaño no puede ser negativo."
        )


    multiplicadores = {
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
    }


    multiplicador = (
        multiplicadores.get(
            unidad,
            1024 ** 2,
        )
    )


    return int(
        numero
        * multiplicador
    )


def _fecha_desde(
    valor: str,
):
    """
    Convierte YYYY-MM-DD al inicio de ese día.
    """

    fecha = parse_date(
        str(
            valor or ""
        )
    )

    if not fecha:
        return None


    resultado = datetime.combine(
        fecha,
        time.min,
    )


    return timezone.make_aware(
        resultado,
        timezone.get_current_timezone(),
    )


def _fecha_hasta(
    valor: str,
):
    """
    Convierte YYYY-MM-DD al final de ese día.
    """

    fecha = parse_date(
        str(
            valor or ""
        )
    )

    if not fecha:
        return None


    resultado = datetime.combine(
        fecha,
        time.max,
    )


    return timezone.make_aware(
        resultado,
        timezone.get_current_timezone(),
    )


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


    extension = (
        _normalizar_extension(
            params.get(
                "extension",
                "",
            )
        )
    )


    texto = str(
        params.get(
            "texto",
            "",
        )
        or ""
    ).strip()


    minimo_valor = str(
        params.get(
            "minimo",
            "",
        )
        or ""
    ).strip()


    minimo_unidad = str(
        params.get(
            "minimo_unidad",
            "MB",
        )
        or "MB"
    ).upper()


    if minimo_unidad not in {
        "KB",
        "MB",
        "GB",
    }:

        minimo_unidad = "MB"


    maximo_valor = str(
        params.get(
            "maximo",
            "",
        )
        or ""
    ).strip()


    maximo_unidad = str(
        params.get(
            "maximo_unidad",
            "MB",
        )
        or "MB"
    ).upper()


    if maximo_unidad not in {
        "KB",
        "MB",
        "GB",
    }:

        maximo_unidad = "MB"


    fecha_desde = str(
        params.get(
            "fecha_desde",
            "",
        )
        or ""
    ).strip()


    fecha_hasta = str(
        params.get(
            "fecha_hasta",
            "",
        )
        or ""
    ).strip()


    orden = str(
        params.get(
            "orden",
            "tamano_desc",
        )
        or "tamano_desc"
    )


    ordenes_validos = {
        codigo
        for codigo, etiqueta
        in ORDENES
    }


    if orden not in ordenes_validos:

        orden = "tamano_desc"


    return {
        "ruta": ruta,

        "tipo": tipo,

        "extension": extension,

        "texto": texto,

        "minimo": minimo_valor,

        "minimo_unidad": minimo_unidad,

        "maximo": maximo_valor,

        "maximo_unidad": maximo_unidad,

        "fecha_desde": fecha_desde,

        "fecha_hasta": fecha_hasta,

        "orden": orden,
    }


# =============================================================================
# CATÁLOGO / FORMULARIO
# =============================================================================


def obtener_configuracion_inventario(
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

        "unidades": (
            UNIDADES
        ),

        "ordenes": (
            ORDENES
        ),

        "filtros": (
            _filtros_desde_params(
                params
            )
        ),
    }


# =============================================================================
# FILTROS
# =============================================================================


def _archivo_coincide(
    *,
    path: Path,
    ruta_relativa: str,
    categoria: str,
    extension: str,
    tamano: int,
    modificado,
    filtros: dict,
    minimo_bytes: int | None,
    maximo_bytes: int | None,
    desde,
    hasta,
) -> bool:


    # =========================================================================
    # TIPO
    # =========================================================================

    if (
        filtros["tipo"]
        and categoria
        != filtros["tipo"]
    ):

        return False


    # =========================================================================
    # EXTENSIÓN
    # =========================================================================

    if (
        filtros["extension"]
        and extension
        != filtros["extension"]
    ):

        return False


    # =========================================================================
    # TEXTO
    # =========================================================================

    if filtros["texto"]:

        buscado = (
            filtros[
                "texto"
            ].casefold()
        )


        if (
            buscado
            not in ruta_relativa.casefold()
        ):

            return False


    # =========================================================================
    # TAMAÑO
    # =========================================================================

    if (
        minimo_bytes is not None
        and tamano < minimo_bytes
    ):

        return False


    if (
        maximo_bytes is not None
        and tamano > maximo_bytes
    ):

        return False


    # =========================================================================
    # FECHA
    # =========================================================================

    if (
        desde is not None
        and modificado < desde
    ):

        return False


    if (
        hasta is not None
        and modificado > hasta
    ):

        return False


    return True


# =============================================================================
# ORDEN
# =============================================================================


def _ordenar_resultados(
    resultados: list,
    orden: str,
) -> None:


    if orden == "tamano_asc":

        resultados.sort(
            key=lambda item: (
                item[
                    "total_bytes"
                ],
                item[
                    "ruta_relativa"
                ].casefold(),
            )
        )

        return


    if orden == "antiguos":

        resultados.sort(
            key=lambda item: (
                item[
                    "modificado"
                ],
                item[
                    "ruta_relativa"
                ].casefold(),
            )
        )

        return


    if orden == "recientes":

        resultados.sort(
            key=lambda item: (
                item[
                    "modificado"
                ]
            ),
            reverse=True,
        )

        return


    if orden == "nombre":

        resultados.sort(
            key=lambda item: (
                item[
                    "ruta_relativa"
                ].casefold()
            )
        )

        return


    # Por defecto:
    # mayor tamaño primero.

    resultados.sort(
        key=lambda item: (
            item[
                "total_bytes"
            ]
        ),
        reverse=True,
    )


# =============================================================================
# INVENTARIO BAJO DEMANDA
# =============================================================================


def buscar_inventario(
    params,
) -> dict:
    """
    ESP010.

    Busca archivos dentro de las RutaMonitoreada activas.

    La búsqueda es exclusivamente de lectura.

    NO:
    - crea modelos;
    - modifica archivos;
    - borra archivos;
    - mueve archivos;
    - sigue symlinks;
    - habilita mantenimiento.
    """

    inicio = (
        perf_counter()
    )


    filtros = (
        _filtros_desde_params(
            params
        )
    )


    resultado = {
        "ejecutado": True,

        "filtros": filtros,

        "archivos": [],

        "coincidencias": 0,

        "total_bytes": 0,

        "total_legible": "0 B",

        "mostrados": 0,

        "ocultos": 0,

        "archivos_examinados": 0,

        "directorios_examinados": 0,

        "enlaces_omitidos": 0,

        "inaccesibles": 0,

        "rutas_analizadas": 0,

        "errores": [],

        "duracion_ms": 0,

        "memoria_limitada": False,

        "archivo_mayor": None,

        "archivo_mas_antiguo": None,

        "archivo_mas_reciente": None,

        "error": "",
    }


    # =========================================================================
    # VALIDAR TAMAÑOS
    # =========================================================================

    try:

        minimo_bytes = (
            _tamano_a_bytes(
                filtros[
                    "minimo"
                ],
                filtros[
                    "minimo_unidad"
                ],
            )
        )


        maximo_bytes = (
            _tamano_a_bytes(
                filtros[
                    "maximo"
                ],
                filtros[
                    "maximo_unidad"
                ],
            )
        )


    except ValueError as exc:

        resultado[
            "error"
        ] = str(
            exc
        )

        return resultado


    if (
        minimo_bytes is not None
        and maximo_bytes is not None
        and minimo_bytes > maximo_bytes
    ):

        resultado[
            "error"
        ] = (
            "El tamaño mínimo no puede "
            "ser mayor que el máximo."
        )

        return resultado


    # =========================================================================
    # VALIDAR FECHAS
    # =========================================================================

    desde = (
        _fecha_desde(
            filtros[
                "fecha_desde"
            ]
        )
    )


    hasta = (
        _fecha_hasta(
            filtros[
                "fecha_hasta"
            ]
        )
    )


    if (
        filtros["fecha_desde"]
        and desde is None
    ):

        resultado[
            "error"
        ] = (
            "La fecha inicial no es válida."
        )

        return resultado


    if (
        filtros["fecha_hasta"]
        and hasta is None
    ):

        resultado[
            "error"
        ] = (
            "La fecha final no es válida."
        )

        return resultado


    if (
        desde is not None
        and hasta is not None
        and desde > hasta
    ):

        resultado[
            "error"
        ] = (
            "La fecha inicial no puede "
            "ser posterior a la fecha final."
        )

        return resultado


    # =========================================================================
    # RUTAS A ANALIZAR
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
                "La ruta seleccionada no es válida."
            )

            return resultado


        rutas_qs = (
            rutas_qs.filter(
                pk=ruta_id
            )
        )


        if not rutas_qs.exists():

            resultado[
                "error"
            ] = (
                "La ruta seleccionada no existe "
                "o no está activa."
            )

            return resultado


    rutas = list(
        rutas_qs
    )


    # =========================================================================
    # EVITAR DUPLICACIÓN POR RUTAS MONITORIZADAS SOLAPADAS
    # =========================================================================
    #
    # Si en el futuro se monitorea:
    #
    #   media/
    #
    # y también:
    #
    #   media/fotos/
    #
    # una búsqueda global no debe contar dos veces
    # el mismo pathname.
    # =========================================================================

    paths_vistos = set()


    coincidencias_en_memoria = []


    ahora = (
        timezone.now()
    )


    # =========================================================================
    # ANALIZAR CADA RUTA
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
                    "ruta": (
                        ruta.nombre
                    ),

                    "detalle": (
                        "La ruta física no existe."
                    ),
                }
            )

            continue


        if not raiz.is_dir():

            resultado[
                "errores"
            ].append(
                {
                    "ruta": (
                        ruta.nombre
                    ),

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


        stack = [
            raiz
        ]


        while stack:

            directorio = (
                stack.pop()
            )


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
                            # SYMLINK
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


                            path_clave = (
                                os.path.normcase(
                                    os.path.abspath(
                                        str(
                                            path
                                        )
                                    )
                                )
                            )


                            # Evitar contar el mismo pathname
                            # por rutas solapadas.

                            if path_clave in paths_vistos:

                                continue


                            paths_vistos.add(
                                path_clave
                            )


                            # =================================================
                            # STAT
                            # =================================================

                            try:

                                stat = (
                                    entrada.stat(
                                        follow_symlinks=False
                                    )
                                )

                            except OSError:

                                resultado[
                                    "inaccesibles"
                                ] += 1

                                continue


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


                            try:

                                relativa = str(
                                    path.relative_to(
                                        raiz
                                    )
                                )

                            except ValueError:

                                resultado[
                                    "inaccesibles"
                                ] += 1

                                continue


                            ruta_presentacion = (
                                f"{ruta.nombre}/"
                                f"{relativa}"
                            )


                            # =================================================
                            # FILTROS
                            # =================================================

                            if not _archivo_coincide(

                                path=path,

                                ruta_relativa=(
                                    ruta_presentacion
                                ),

                                categoria=(
                                    categoria
                                ),

                                extension=(
                                    extension
                                ),

                                tamano=(
                                    tamano
                                ),

                                modificado=(
                                    modificado
                                ),

                                filtros=(
                                    filtros
                                ),

                                minimo_bytes=(
                                    minimo_bytes
                                ),

                                maximo_bytes=(
                                    maximo_bytes
                                ),

                                desde=(
                                    desde
                                ),

                                hasta=(
                                    hasta
                                ),
                            ):

                                continue


                            # =================================================
                            # COINCIDENCIA
                            # =================================================

                            resultado[
                                "coincidencias"
                            ] += 1


                            resultado[
                                "total_bytes"
                            ] += tamano


                            antiguedad = max(
                                (
                                    ahora
                                    - modificado
                                ).days,
                                0,
                            )


                            tipos_interes = (
                                ruta.tipos_interes
                                or []
                            )


                            extensiones_interes = (
                                ruta.extensiones_interes
                                or []
                            )


                            item = {
                                "ruta_id": (
                                    ruta.pk
                                ),

                                "ruta_nombre": (
                                    ruta.nombre
                                ),

                                "nombre": (
                                    path.name
                                ),

                                "ruta_relativa": (
                                    relativa
                                ),

                                "ruta_presentacion": (
                                    ruta_presentacion
                                ),

                                "ruta_absoluta": (
                                    str(
                                        path
                                    )
                                ),

                                "categoria_codigo": (
                                    categoria
                                ),

                                "categoria": (
                                    nombre_categoria(
                                        categoria
                                    )
                                ),

                                "extension": (
                                    extension
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

                                "antiguedad_dias": (
                                    antiguedad
                                ),

                                "tipo_interes": (
                                    categoria
                                    in tipos_interes
                                ),

                                "extension_interes": (
                                    extension
                                    in extensiones_interes
                                ),
                            }


                            # =================================================
                            # MAYOR
                            # =================================================

                            mayor = (
                                resultado[
                                    "archivo_mayor"
                                ]
                            )


                            if (
                                mayor is None
                                or tamano
                                > mayor[
                                    "total_bytes"
                                ]
                            ):

                                resultado[
                                    "archivo_mayor"
                                ] = item


                            # =================================================
                            # MÁS ANTIGUO
                            # =================================================

                            antiguo = (
                                resultado[
                                    "archivo_mas_antiguo"
                                ]
                            )


                            if (
                                antiguo is None
                                or modificado
                                < antiguo[
                                    "modificado"
                                ]
                            ):

                                resultado[
                                    "archivo_mas_antiguo"
                                ] = item


                            # =================================================
                            # MÁS RECIENTE
                            # =================================================

                            reciente = (
                                resultado[
                                    "archivo_mas_reciente"
                                ]
                            )


                            if (
                                reciente is None
                                or modificado
                                > reciente[
                                    "modificado"
                                ]
                            ):

                                resultado[
                                    "archivo_mas_reciente"
                                ] = item


                            # =================================================
                            # CONSERVAR PARA TABLA
                            # =================================================

                            if (
                                len(
                                    coincidencias_en_memoria
                                )
                                <
                                MAX_COINCIDENCIAS_EN_MEMORIA
                            ):

                                coincidencias_en_memoria.append(
                                    item
                                )

                            else:

                                resultado[
                                    "memoria_limitada"
                                ] = True


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
    # ORDENAR
    # =========================================================================

    _ordenar_resultados(
        coincidencias_en_memoria,
        filtros[
            "orden"
        ],
    )


    # =========================================================================
    # LIMITAR PRESENTACIÓN
    # =========================================================================

    resultado[
        "archivos"
    ] = (
        coincidencias_en_memoria[
            :MAX_RESULTADOS_MOSTRADOS
        ]
    )


    resultado[
        "mostrados"
    ] = len(
        resultado[
            "archivos"
        ]
    )


    resultado[
        "ocultos"
    ] = max(
        (
            resultado[
                "coincidencias"
            ]
            -
            resultado[
                "mostrados"
            ]
        ),
        0,
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