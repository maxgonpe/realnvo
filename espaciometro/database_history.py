from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import (
    EjecucionMedicion,
    MedicionBaseDatos,
)


# =============================================================================
# ESP021 — HISTÓRICO DE BASE DE DATOS
# =============================================================================
#
# PRINCIPIOS:
#
# - Solo analiza mediciones ya persistidas por Espaciómetro.
# - No consulta ni modifica tablas de negocio.
# - No ejecuta DELETE / UPDATE / ALTER.
# - Descarta automáticamente ejecuciones sin MedicionTabla.
# - Mantiene el mismo criterio de tendencia utilizado por ESP009.
# =============================================================================


UMBRAL_ESTABLE_PORCENTAJE = 1.0


# =============================================================================
# UTILIDADES
# =============================================================================


def _numero_legible(
    valor: Any,
) -> str:

    if valor is None:
        return "-"

    try:

        numero = int(
            valor
        )

    except (
        TypeError,
        ValueError,
    ):

        return "-"


    return f"{numero:,}".replace(
        ",",
        ".",
    )


def _numero_con_signo(
    valor: Any,
) -> str:

    if valor is None:
        return "-"

    try:

        numero = float(
            valor
        )

    except (
        TypeError,
        ValueError,
    ):

        return "-"


    if numero == 0:
        return "0"


    if numero.is_integer():

        texto = (
            f"{int(abs(numero)):,}"
            .replace(
                ",",
                ".",
            )
        )

    else:

        texto = (
            f"{abs(numero):,.2f}"
            .replace(
                ",",
                "_",
            )
            .replace(
                ".",
                ",",
            )
            .replace(
                "_",
                ".",
            )
        )


    if numero > 0:
        return f"+{texto}"

    return f"-{texto}"


def _porcentaje_variacion(
    inicial: int,
    final: int,
) -> float | None:

    if inicial == 0:

        if final == 0:
            return 0.0

        return None


    return round(
        (
            (
                final
                - inicial
            )
            / inicial
        )
        * 100,
        2,
    )


def _porcentaje_texto(
    porcentaje: float | None,
) -> str:

    if porcentaje is None:
        return "-"

    if porcentaje > 0:
        return f"+{porcentaje:.2f} %"

    return f"{porcentaje:.2f} %"


# =============================================================================
# TENDENCIA
# =============================================================================


def _calcular_tendencia(
    inicial: int,
    final: int,
) -> dict:

    if inicial == final:

        return {
            "codigo": "ESTABLE",
            "simbolo": "→",
            "texto": "Estable",
        }


    porcentaje = (
        _porcentaje_variacion(
            inicial,
            final,
        )
    )


    if porcentaje is None:

        if final > inicial:

            return {
                "codigo": "CRECIENDO",
                "simbolo": "↑",
                "texto": "Creciendo",
            }

        return {
            "codigo": "DISMINUYENDO",
            "simbolo": "↓",
            "texto": "Disminuyendo",
        }


    if (
        abs(
            porcentaje
        )
        < UMBRAL_ESTABLE_PORCENTAJE
    ):

        return {
            "codigo": "ESTABLE",
            "simbolo": "→",
            "texto": "Estable",
        }


    if porcentaje > 0:

        return {
            "codigo": "CRECIENDO",
            "simbolo": "↑",
            "texto": "Creciendo",
        }


    return {
        "codigo": "DISMINUYENDO",
        "simbolo": "↓",
        "texto": "Disminuyendo",
    }


# =============================================================================
# RESUMEN DE SERIE DE REGISTROS
# =============================================================================


def _resumir_serie_registros(
    puntos: list[dict],
) -> dict:

    if not puntos:

        return {
            "disponible": False,

            "puede_calcular_tendencia": False,

            "mediciones": 0,

            "dias_observados": 0,

            "tendencia": {
                "codigo": "SIN_DATOS",
                "simbolo": "·",
                "texto": "Sin datos",
            },
        }


    primera = puntos[0]

    ultima = puntos[-1]


    inicial = int(
        primera[
            "registros"
        ]
        or 0
    )

    actual = int(
        ultima[
            "registros"
        ]
        or 0
    )


    variacion_total = (
        actual
        - inicial
    )


    porcentaje_total = (
        _porcentaje_variacion(
            inicial,
            actual,
        )
    )


    segundos = max(
        (
            ultima["fecha"]
            - primera["fecha"]
        ).total_seconds(),
        0,
    )


    dias_exactos = (
        segundos
        / 86400
    )


    if dias_exactos > 0:

        promedio_dia = (
            variacion_total
            / dias_exactos
        )

    else:

        promedio_dia = None


    # =========================================================================
    # COMPARACIÓN CON MEDICIÓN ANTERIOR
    # =========================================================================

    variacion_anterior = None

    porcentaje_anterior = None


    if len(
        puntos
    ) >= 2:

        anterior = puntos[
            -2
        ]


        valor_anterior = int(
            anterior[
                "registros"
            ]
            or 0
        )


        variacion_anterior = (
            actual
            - valor_anterior
        )


        porcentaje_anterior = (
            _porcentaje_variacion(
                valor_anterior,
                actual,
            )
        )


    # =========================================================================
    # TENDENCIA
    # =========================================================================

    if len(
        puntos
    ) >= 2:

        tendencia = (
            _calcular_tendencia(
                inicial,
                actual,
            )
        )

    else:

        tendencia = {
            "codigo": "SIN_DATOS",
            "simbolo": "·",
            "texto": (
                "Se necesita otra medición"
            ),
        }


    return {
        "disponible": True,

        "puede_calcular_tendencia": (
            len(
                puntos
            )
            >= 2
        ),

        "mediciones": len(
            puntos
        ),

        "primera_fecha": (
            primera[
                "fecha"
            ]
        ),

        "ultima_fecha": (
            ultima[
                "fecha"
            ]
        ),

        "valor_inicial": (
            inicial
        ),

        "valor_inicial_legible": (
            _numero_legible(
                inicial
            )
        ),

        "valor_actual": (
            actual
        ),

        "valor_actual_legible": (
            _numero_legible(
                actual
            )
        ),

        "variacion_total": (
            variacion_total
        ),

        "variacion_total_legible": (
            _numero_con_signo(
                variacion_total
            )
        ),

        "porcentaje_total": (
            porcentaje_total
        ),

        "porcentaje_total_texto": (
            _porcentaje_texto(
                porcentaje_total
            )
        ),

        "variacion_anterior": (
            variacion_anterior
        ),

        "variacion_anterior_legible": (
            _numero_con_signo(
                variacion_anterior
            )
        ),

        "porcentaje_anterior": (
            porcentaje_anterior
        ),

        "porcentaje_anterior_texto": (
            _porcentaje_texto(
                porcentaje_anterior
            )
        ),

        "dias_observados": round(
            dias_exactos,
            1,
        ),

        "promedio_dia": (
            promedio_dia
        ),

        "promedio_dia_legible": (
            _numero_con_signo(
                promedio_dia
            )
            if promedio_dia is not None
            else "-"
        ),

        "tendencia": (
            tendencia
        ),
    }


# =============================================================================
# FOTOGRAFÍAS VÁLIDAS
# =============================================================================


def obtener_fotografias_validas(
    *,
    alias="default",
):

    """
    Obtiene únicamente fotografías históricas reales de ESP021.

    Una MedicionBaseDatos es válida para ESP021 cuando:

    - pertenece a una ejecución COMPLETADA o PARCIAL;
    - corresponde al alias solicitado;
    - contiene al menos una MedicionTabla.

    Esto excluye automáticamente las mediciones generales de ESP004
    y ejecuciones fallidas como la fotografía #6 de desarrollo.
    """

    return (
        MedicionBaseDatos
        .objects
        .filter(
            alias=alias,

            ejecucion__estado__in=[
                EjecucionMedicion
                .Estado
                .COMPLETADA,

                EjecucionMedicion
                .Estado
                .PARCIAL,
            ],

            tablas__isnull=False,
        )
        .select_related(
            "ejecucion"
        )
        .distinct()
        .order_by(
            "ejecucion__iniciada_en",
            "id",
        )
    )


# =============================================================================
# HISTÓRICO POR TABLA
# =============================================================================


def obtener_historico_tablas(
    *,
    alias="default",
) -> list[dict]:

    fotografias = list(
        obtener_fotografias_validas(
            alias=alias
        )
    )


    series = defaultdict(
        list
    )


    for fotografia in fotografias:

        tablas = (
            fotografia
            .tablas
            .all()
            .order_by(
                "nombre_tabla"
            )
        )


        for tabla in tablas:

            # =============================================================
            # ESP021 — EVITAR AUTO-MEDICIÓN
            # =============================================================
            #
            # Las tablas internas de Espaciómetro se conservan en la
            # fotografía RAW, pero no participan en el cálculo de
            # crecimiento del proyecto.
            # =============================================================

            if tabla.nombre_tabla.startswith(
                "esp_"
            ):

                continue


            if (
                tabla.total_registros
                is None
            ):

                continue


            clave = (
                tabla.esquema or "",
                tabla.nombre_tabla,
            )


            series[
                clave
            ].append(
                {
                    "fecha": (
                        fotografia
                        .ejecucion
                        .iniciada_en
                    ),

                    "ejecucion_id": (
                        fotografia
                        .ejecucion_id
                    ),

                    "medicion_bd_id": (
                        fotografia.pk
                    ),

                    "registros": int(
                        tabla.total_registros
                    ),
                }
            )


    resultado = []


    for (
        esquema,
        nombre_tabla,
    ), puntos in series.items():

        resumen = (
            _resumir_serie_registros(
                puntos
            )
        )


        resultado.append(
            {
                "esquema": esquema,

                "nombre_tabla": (
                    nombre_tabla
                ),

                "nombre_completo": (
                    f"{esquema}.{nombre_tabla}"
                    if esquema
                    else nombre_tabla
                ),

                "puntos": puntos,

                "resumen": resumen,

                "tendencia": (
                    resumen[
                        "tendencia"
                    ]
                ),
            }
        )


    resultado.sort(
        key=lambda item: (
            -abs(
                item[
                    "resumen"
                ].get(
                    "variacion_total",
                    0,
                )
                or 0
            ),
            item[
                "nombre_completo"
            ],
        )
    )


    return resultado


# =============================================================================
# PANEL GENERAL ESP021
# =============================================================================


def obtener_panel_historico_base_datos(
    *,
    alias="default",
) -> dict:

    fotografias = list(
        obtener_fotografias_validas(
            alias=alias
        )
    )


    tablas = (
        obtener_historico_tablas(
            alias=alias
        )
    )


    creciendo = sum(
        1
        for tabla in tablas
        if tabla[
            "tendencia"
        ][
            "codigo"
        ] == "CRECIENDO"
    )


    estables = sum(
        1
        for tabla in tablas
        if tabla[
            "tendencia"
        ][
            "codigo"
        ] == "ESTABLE"
    )


    disminuyendo = sum(
        1
        for tabla in tablas
        if tabla[
            "tendencia"
        ][
            "codigo"
        ] == "DISMINUYENDO"
    )


    sin_datos = sum(
        1
        for tabla in tablas
        if tabla[
            "tendencia"
        ][
            "codigo"
        ] == "SIN_DATOS"
    )


    ultima = (
        fotografias[
            -1
        ]
        if fotografias
        else None
    )

    # =========================================================================
    # MÉTRICAS DE LA ÚLTIMA FOTOGRAFÍA
    # =========================================================================
    #
    # Separamos:
    #
    # - RAW: todo lo observado en la base.
    # - ANALIZADO: excluye las tablas internas esp_* para evitar
    #   que Espaciómetro mida su propio crecimiento.
    # =========================================================================

    tablas_fotografiadas = 0
    registros_fotografiados = 0

    tablas_analizadas = 0
    registros_analizados = 0

    tablas_excluidas = 0
    registros_excluidos = 0


    if ultima:

        tablas_fotografiadas = int(
            ultima.total_tablas
            or 0
        )

        registros_fotografiados = int(
            ultima.total_registros
            or 0
        )


        for tabla in ultima.tablas.all():

            cantidad = int(
                tabla.total_registros
                or 0
            )


            if tabla.nombre_tabla.startswith(
                "esp_"
            ):

                tablas_excluidas += 1

                registros_excluidos += (
                    cantidad
                )

            else:

                tablas_analizadas += 1

                registros_analizados += (
                    cantidad
                )


    return {
        "alias": alias,

        "fotografias": (
            fotografias
        ),

        "total_fotografias": len(
            fotografias
        ),

        "ultima_fotografia": (
            ultima
        ),

        "tablas": (
            tablas
        ),

        "total_tablas": len(
            tablas
        ),

        # =====================================================================
        # MÉTRICAS RAW / ANALIZADAS DE LA ÚLTIMA FOTOGRAFÍA
        # =====================================================================

        "tablas_fotografiadas": (
            tablas_fotografiadas
        ),

        "registros_fotografiados": (
            registros_fotografiados
        ),

        "tablas_analizadas": (
            tablas_analizadas
        ),

        "registros_analizados": (
            registros_analizados
        ),

        "tablas_excluidas": (
            tablas_excluidas
        ),

        "registros_excluidos": (
            registros_excluidos
        ),

        "creciendo": (
            creciendo
        ),

        "estables": (
            estables
        ),

        "disminuyendo": (
            disminuyendo
        ),

        "sin_datos": (
            sin_datos
        ),

        "puede_calcular_crecimiento": (
            len(
                fotografias
            )
            >= 2
        ),
    }