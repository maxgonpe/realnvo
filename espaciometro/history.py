from __future__ import annotations

from typing import Any

from .models import (
    MedicionDisco,
    MedicionRuta,
    RutaMonitoreada,
    bytes_legibles,
)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

UMBRAL_ESTABLE_PORCENTAJE = 1.0


# =============================================================================
# UTILIDADES
# =============================================================================


def _entero(objeto: Any, *nombres: str) -> int:
    """
    Obtiene un entero intentando varios nombres de atributo.

    Permite tolerar pequeñas diferencias de nombres internos
    entre versiones del modelo.
    """

    for nombre in nombres:

        if not hasattr(objeto, nombre):
            continue

        valor = getattr(
            objeto,
            nombre,
            None,
        )

        try:
            return int(
                valor or 0
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

    return 0


def _decimal(objeto: Any, *nombres: str) -> float:

    for nombre in nombres:

        if not hasattr(objeto, nombre):
            continue

        valor = getattr(
            objeto,
            nombre,
            None,
        )

        try:
            return float(
                valor or 0
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

    return 0.0


def _texto(objeto: Any, *nombres: str) -> str:

    for nombre in nombres:

        if not hasattr(objeto, nombre):
            continue

        valor = getattr(
            objeto,
            nombre,
            None,
        )

        if valor:
            return str(
                valor
            )

    return ""


def _bytes_con_signo(
    valor: int | float | None,
) -> str:

    if valor is None:
        return "-"

    valor = int(
        valor
    )

    if valor > 0:

        return (
            "+"
            + bytes_legibles(
                valor
            )
        )

    if valor < 0:

        return (
            "-"
            + bytes_legibles(
                abs(valor)
            )
        )

    return "0 B"


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
# GRÁFICO
# =============================================================================


def _preparar_grafico(
    puntos: list[dict],
    campo_valor: str,
) -> dict:

    if not puntos:

        return {
            "disponible": False,
            "puntos": "",
            "minimo_legible": "-",
            "maximo_legible": "-",
        }


    valores = [
        int(
            punto[
                campo_valor
            ]
        )
        for punto in puntos
    ]


    minimo = min(
        valores
    )

    maximo = max(
        valores
    )


    primera_fecha = puntos[
        0
    ]["fecha"]

    ultima_fecha = puntos[
        -1
    ]["fecha"]


    rango_tiempo = (
        ultima_fecha
        - primera_fecha
    ).total_seconds()


    rango_valor = (
        maximo
        - minimo
    )


    coordenadas = []


    for indice, punto in enumerate(
        puntos
    ):

        # =====================================================================
        # COORDENADA X
        # =====================================================================

        if rango_tiempo > 0:

            transcurrido = (
                punto["fecha"]
                - primera_fecha
            ).total_seconds()


            x = (
                5
                + (
                    transcurrido
                    / rango_tiempo
                )
                * 90
            )

        elif len(
            puntos
        ) > 1:

            x = (
                5
                + (
                    indice
                    / (
                        len(
                            puntos
                        )
                        - 1
                    )
                )
                * 90
            )

        else:

            x = 50


        # =====================================================================
        # COORDENADA Y
        # =====================================================================

        if rango_valor > 0:

            posicion = (
                (
                    punto[
                        campo_valor
                    ]
                    - minimo
                )
                / rango_valor
            )


            y = (
                35
                - posicion
                * 30
            )

        else:

            y = 20


        punto[
            "grafico_x"
        ] = round(
            x,
            2,
        )


        punto[
            "grafico_y"
        ] = round(
            y,
            2,
        )


        coordenadas.append(
            (
                f"{punto['grafico_x']},"
                f"{punto['grafico_y']}"
            )
        )


    return {
        "disponible": True,

        "puntos": " ".join(
            coordenadas
        ),

        "minimo": minimo,

        "maximo": maximo,

        "minimo_legible": (
            bytes_legibles(
                minimo
            )
        ),

        "maximo_legible": (
            bytes_legibles(
                maximo
            )
        ),
    }


# =============================================================================
# RESUMEN DE UNA SERIE
# =============================================================================


def _resumir_serie(
    puntos: list[dict],
    campo_valor: str,
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


    primera = puntos[
        0
    ]

    ultima = puntos[
        -1
    ]


    primer_valor = int(
        primera[
            campo_valor
        ]
    )

    ultimo_valor = int(
        ultima[
            campo_valor
        ]
    )


    diferencia_total = (
        ultimo_valor
        - primer_valor
    )


    porcentaje_total = (
        _porcentaje_variacion(
            primer_valor,
            ultimo_valor,
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
            diferencia_total
            / dias_exactos
        )

    else:

        promedio_dia = None


    # =========================================================================
    # MEDICIÓN ANTERIOR
    # =========================================================================

    diferencia_anterior = None

    porcentaje_anterior = None


    if len(
        puntos
    ) >= 2:

        anterior = puntos[
            -2
        ]


        valor_anterior = int(
            anterior[
                campo_valor
            ]
        )


        diferencia_anterior = (
            ultimo_valor
            - valor_anterior
        )


        porcentaje_anterior = (
            _porcentaje_variacion(
                valor_anterior,
                ultimo_valor,
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
                primer_valor,
                ultimo_valor,
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
            primer_valor
        ),

        "valor_inicial_legible": (
            bytes_legibles(
                primer_valor
            )
        ),

        "valor_actual": (
            ultimo_valor
        ),

        "valor_actual_legible": (
            bytes_legibles(
                ultimo_valor
            )
        ),

        "variacion_total": (
            diferencia_total
        ),

        "variacion_total_legible": (
            _bytes_con_signo(
                diferencia_total
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
            diferencia_anterior
        ),

        "variacion_anterior_legible": (
            _bytes_con_signo(
                diferencia_anterior
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
            _bytes_con_signo(
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
# HISTÓRICO DE UNA RUTA
# =============================================================================


def obtener_evolucion_ruta(
    ruta: RutaMonitoreada,
) -> dict:

    mediciones = (
        MedicionRuta.objects
        .filter(
            ruta_monitoreada=ruta
        )
        .select_related(
            "ejecucion"
        )
        .order_by(
            "ejecucion__iniciada_en",
            "pk",
        )
    )


    puntos = []

    mediciones_con_error = []


    for medicion in mediciones:

        error = str(
            getattr(
                medicion,
                "error",
                "",
            )
            or ""
        )


        punto = {
            "id": (
                medicion.pk
            ),

            "ejecucion_id": (
                medicion.ejecucion_id
            ),

            "fecha": (
                medicion
                .ejecucion
                .iniciada_en
            ),

            "estado_ejecucion": (
                medicion
                .ejecucion
                .estado
            ),

            "total_bytes": _entero(
                medicion,
                "total_bytes",
            ),

            "total_archivos": _entero(
                medicion,
                "total_archivos",
            ),

            "total_directorios": _entero(
                medicion,
                "total_directorios",
            ),

            "inaccesibles": _entero(
                medicion,
                "archivos_inaccesibles",
                "inaccesibles",
            ),

            "error": (
                error
            ),
        }


        punto[
            "total_legible"
        ] = bytes_legibles(
            punto[
                "total_bytes"
            ]
        )


        if error:

            mediciones_con_error.append(
                punto
            )

            continue


        puntos.append(
            punto
        )


    resumen = (
        _resumir_serie(
            puntos,
            "total_bytes",
        )
    )


    grafico = (
        _preparar_grafico(
            puntos,
            "total_bytes",
        )
    )


    return {
        "ruta_id": (
            ruta.pk
        ),

        "nombre": (
            ruta.nombre
        ),

        "ruta": (
            ruta.ruta
        ),

        "categoria": (
            ruta.get_categoria_display()
        ),

        "activa": (
            ruta.activa
        ),

        "puntos": (
            puntos
        ),

        "resumen": (
            resumen
        ),

        "grafico": (
            grafico
        ),

        "mediciones_total": (
            len(
                puntos
            )
            + len(
                mediciones_con_error
            )
        ),

        "mediciones_validas": len(
            puntos
        ),

        "mediciones_con_error": (
            mediciones_con_error
        ),

        "total_con_error": len(
            mediciones_con_error
        ),
    }


# =============================================================================
# RESUMEN DE TODAS LAS RUTAS
# =============================================================================


def obtener_resumen_crecimiento_rutas() -> list[dict]:

    rutas = (
        RutaMonitoreada.objects
        .filter(
            visible_dashboard=True
        )
        .order_by(
            "nombre"
        )
    )


    resultado = []


    for ruta in rutas:

        evolucion = (
            obtener_evolucion_ruta(
                ruta
            )
        )


        resumen = (
            evolucion[
                "resumen"
            ]
        )


        resultado.append(
            {
                "id": (
                    ruta.pk
                ),

                "nombre": (
                    ruta.nombre
                ),

                "ruta": (
                    ruta.ruta
                ),

                "activa": (
                    ruta.activa
                ),

                "mediciones": (
                    resumen.get(
                        "mediciones",
                        0,
                    )
                ),

                "actual_legible": (
                    resumen.get(
                        "valor_actual_legible",
                        "-"
                    )
                ),

                "variacion_legible": (
                    resumen.get(
                        "variacion_total_legible",
                        "-"
                    )
                ),

                "porcentaje_texto": (
                    resumen.get(
                        "porcentaje_total_texto",
                        "-"
                    )
                ),

                "dias_observados": (
                    resumen.get(
                        "dias_observados",
                        0,
                    )
                ),

                "promedio_dia_legible": (
                    resumen.get(
                        "promedio_dia_legible",
                        "-"
                    )
                ),

                "tendencia": (
                    resumen.get(
                        "tendencia"
                    )
                    or {
                        "codigo": "SIN_DATOS",
                        "simbolo": "·",
                        "texto": "Sin datos",
                    }
                ),
            }
        )


    orden = {
        "CRECIENDO": 0,
        "DISMINUYENDO": 1,
        "ESTABLE": 2,
        "SIN_DATOS": 3,
    }


    resultado.sort(
        key=lambda item: (
            orden.get(
                item[
                    "tendencia"
                ][
                    "codigo"
                ],
                9,
            ),

            item[
                "nombre"
            ].lower(),
        )
    )


    return resultado


# =============================================================================
# HISTÓRICO DEL DISCO
# =============================================================================


def obtener_evolucion_disco() -> dict:
    """
    Histórico global del almacenamiento observado por ESP004.

    IMPORTANTE:
    Los nombres reales del modelo MedicionDisco son:

        total_bytes
        usados_bytes
        libres_bytes
        porcentaje_usado

    ESP009 mantiene también algunos alias como tolerancia
    por si el componente se reutiliza posteriormente.
    """

    mediciones = (
        MedicionDisco.objects
        .select_related(
            "ejecucion"
        )
        .order_by(
            "ejecucion__iniciada_en",
            "pk",
        )
    )


    puntos = []


    for medicion in mediciones:

        total_bytes = _entero(
            medicion,
            "total_bytes",
        )


        # =====================================================================
        # CORRECCIÓN ESP009
        # =====================================================================
        #
        # El modelo utiliza "usados_bytes", no "usado_bytes".
        # =====================================================================

        usados_bytes = _entero(
            medicion,

            "usados_bytes",

            # Alias tolerados:
            "usado_bytes",
            "used_bytes",
            "bytes_usados",
        )


        # =====================================================================
        # CORRECCIÓN ESP009
        # =====================================================================
        #
        # El modelo utiliza "libres_bytes", no "libre_bytes".
        # =====================================================================

        libres_bytes = _entero(
            medicion,

            "libres_bytes",

            # Alias tolerados:
            "libre_bytes",
            "free_bytes",
            "bytes_libres",
        )


        porcentaje = _decimal(
            medicion,
            "porcentaje_usado",
            "porcentaje",
        )


        punto = {
            "id": (
                medicion.pk
            ),

            "ejecucion_id": (
                medicion.ejecucion_id
            ),

            "fecha": (
                medicion
                .ejecucion
                .iniciada_en
            ),

            "total_bytes": (
                total_bytes
            ),

            # Conservamos estos nombres internos para
            # que el resto de ESP009 no necesite cambiar.

            "usado_bytes": (
                usados_bytes
            ),

            "libre_bytes": (
                libres_bytes
            ),

            "porcentaje_usado": (
                porcentaje
            ),

            "punto_montaje": _texto(
                medicion,
                "punto_montaje",
                "mount_point",
            ),
        }


        punto[
            "total_legible"
        ] = bytes_legibles(
            total_bytes
        )


        punto[
            "usado_legible"
        ] = bytes_legibles(
            usados_bytes
        )


        punto[
            "libre_legible"
        ] = bytes_legibles(
            libres_bytes
        )


        puntos.append(
            punto
        )


    resumen = (
        _resumir_serie(
            puntos,
            "usado_bytes",
        )
    )


    grafico = (
        _preparar_grafico(
            puntos,
            "usado_bytes",
        )
    )


    return {
        "puntos": (
            puntos
        ),

        "resumen": (
            resumen
        ),

        "grafico": (
            grafico
        ),
    }


# =============================================================================
# PANEL GENERAL ESP009
# =============================================================================


def obtener_panel_historico() -> dict:

    rutas = (
        obtener_resumen_crecimiento_rutas()
    )


    disco = (
        obtener_evolucion_disco()
    )


    creciendo = sum(
        1
        for ruta in rutas
        if ruta[
            "tendencia"
        ][
            "codigo"
        ] == "CRECIENDO"
    )


    estables = sum(
        1
        for ruta in rutas
        if ruta[
            "tendencia"
        ][
            "codigo"
        ] == "ESTABLE"
    )


    disminuyendo = sum(
        1
        for ruta in rutas
        if ruta[
            "tendencia"
        ][
            "codigo"
        ] == "DISMINUYENDO"
    )


    sin_datos = sum(
        1
        for ruta in rutas
        if ruta[
            "tendencia"
        ][
            "codigo"
        ] == "SIN_DATOS"
    )


    return {
        "rutas": (
            rutas
        ),

        "disco": (
            disco
        ),

        "total_rutas": len(
            rutas
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
    }