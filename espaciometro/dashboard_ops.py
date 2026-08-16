from __future__ import annotations

from .classifier import CATEGORIAS
from .models import RutaMonitoreada


# =============================================================================
# CAMPOS DISPONIBLES
# =============================================================================


CAMPO_POR_TIPO = {
    "imagen": "total_imagenes",
    "pdf": "total_pdf",
    "documento": "total_documentos",
    "planilla": "total_planillas",
    "video": "total_videos",
    "comprimido": "total_comprimidos",
    "temporal": "total_temporales",
    "otro": "total_otros",

    "audio": None,
    "base_datos": None,
    "codigo": None,
    "configuracion": None,
}


# =============================================================================
# CAPACIDAD
# =============================================================================


def _estado_capacidad(
    porcentaje_usado: float,
) -> dict:

    if porcentaje_usado >= 85:

        return {
            "codigo": "CRITICO",
            "texto": "Crítico",
            "descripcion": (
                "El uso del disco requiere atención."
            ),
        }


    if porcentaje_usado >= 70:

        return {
            "codigo": "ATENCION",
            "texto": "Atención",
            "descripcion": (
                "El consumo de disco comienza "
                "a ser significativo."
            ),
        }


    return {
        "codigo": "NORMAL",
        "texto": "Normal",
        "descripcion": (
            "El almacenamiento se encuentra "
            "dentro del rango operativo."
        ),
    }


# =============================================================================
# ESTADO GENERAL
# =============================================================================


def _estado_general(
    *,
    porcentaje_usado: float,
    rutas_con_error: int,
    ultima_medicion,
) -> dict:

    estado = (
        _estado_capacidad(
            porcentaje_usado
        )
    )


    if (
        rutas_con_error
        and estado[
            "codigo"
        ] != "CRITICO"
    ):

        estado = {
            "codigo": "ATENCION",
            "texto": "Atención",
            "descripcion": (
                f"{rutas_con_error} ruta(s) "
                "presentan problemas de lectura "
                "o análisis."
            ),
        }


    if ultima_medicion:

        if (
            ultima_medicion.estado
            == "ERROR"
        ):

            estado = {
                "codigo": "CRITICO",
                "texto": "Crítico",
                "descripcion": (
                    "La última medición histórica "
                    "terminó con errores."
                ),
            }


        elif (
            ultima_medicion.estado
            == "PARCIAL"
            and estado[
                "codigo"
            ] == "NORMAL"
        ):

            estado = {
                "codigo": "ATENCION",
                "texto": "Atención",
                "descripcion": (
                    "La última medición histórica "
                    "terminó parcialmente."
                ),
            }


    return estado


# =============================================================================
# RUTAS
# =============================================================================


def _construir_rutas(
    rutas_live: list,
) -> tuple[list, int]:

    configuraciones = {
        ruta.nombre: ruta

        for ruta
        in RutaMonitoreada.objects.filter(
            activa=True,
            visible_dashboard=True,
        )
    }


    total_bytes = sum(
        int(
            ruta.get(
                "total_bytes",
                0,
            )
            or 0
        )
        for ruta in rutas_live
    )


    resultado = []

    rutas_con_error = 0


    for ruta in rutas_live:

        nombre = (
            ruta.get(
                "nombre",
                "",
            )
        )


        configuracion = (
            configuraciones.get(
                nombre
            )
        )


        bytes_ruta = int(
            ruta.get(
                "total_bytes",
                0,
            )
            or 0
        )


        porcentaje_monitorizado = 0.0


        if total_bytes:

            porcentaje_monitorizado = round(
                (
                    bytes_ruta
                    / total_bytes
                )
                * 100,
                1,
            )


        error = str(
            ruta.get(
                "error",
                "",
            )
            or ""
        )


        inaccesibles = int(
            ruta.get(
                "archivos_inaccesibles",
                0,
            )
            or 0
        )


        tiene_problema = bool(
            error
            or inaccesibles
        )


        if tiene_problema:

            rutas_con_error += 1


        intereses = []


        if configuracion:

            for codigo in (
                configuracion
                .tipos_interes
                or []
            ):

                intereses.append(
                    CATEGORIAS.get(
                        codigo,
                        codigo,
                    )
                )


        resultado.append(
            {
                **ruta,

                # ESP008 necesita este ID.
                "ruta_id": (
                    configuracion.pk
                    if configuracion
                    else None
                ),

                "porcentaje_monitorizado": (
                    porcentaje_monitorizado
                ),

                "tipos_interes_display": (
                    intereses
                ),

                "total_tipos_interes": len(
                    intereses
                ),

                "tiene_problema": (
                    tiene_problema
                ),

                "estado_texto": (
                    "Revisar"
                    if tiene_problema
                    else "Normal"
                ),
            }
        )


    resultado.sort(
        key=lambda item: int(
            item.get(
                "total_bytes",
                0,
            )
            or 0
        ),
        reverse=True,
    )


    return (
        resultado,
        rutas_con_error,
    )


# =============================================================================
# TIPOS DE INTERÉS
# =============================================================================


def _construir_tipos_interes(
    rutas_live: list,
) -> list:

    live_por_nombre = {
        ruta.get(
            "nombre",
            "",
        ): ruta

        for ruta
        in rutas_live
    }


    resumen = {}


    configuraciones = (
        RutaMonitoreada.objects
        .filter(
            activa=True,
            visible_dashboard=True,
        )
        .order_by("nombre")
    )


    for configuracion in configuraciones:

        live = (
            live_por_nombre.get(
                configuracion.nombre,
                {},
            )
        )


        for codigo in (
            configuracion
            .tipos_interes
            or []
        ):

            if codigo not in resumen:

                resumen[codigo] = {
                    "codigo": codigo,

                    "nombre": (
                        CATEGORIAS.get(
                            codigo,
                            codigo,
                        )
                    ),

                    "rutas": 0,

                    "archivos": 0,

                    "conteo_disponible": True,

                    "extensiones": set(),
                }


            item = (
                resumen[
                    codigo
                ]
            )


            item[
                "rutas"
            ] += 1


            campo = (
                CAMPO_POR_TIPO.get(
                    codigo
                )
            )


            if campo:

                item[
                    "archivos"
                ] += int(
                    live.get(
                        campo,
                        0,
                    )
                    or 0
                )

            else:

                item[
                    "conteo_disponible"
                ] = False


        extensiones = (
            configuracion
            .extensiones_interes
            or []
        )


        for codigo in (
            configuracion
            .tipos_interes
            or []
        ):

            if codigo not in resumen:

                continue


            resumen[
                codigo
            ]["extensiones"].update(
                extensiones
            )


    resultado = []


    for item in resumen.values():

        item[
            "extensiones"
        ] = sorted(
            item[
                "extensiones"
            ]
        )


        resultado.append(
            item
        )


    resultado.sort(
        key=lambda item: (
            -item["rutas"],
            item["nombre"].lower(),
        )
    )


    return resultado


# =============================================================================
# ESP007
# =============================================================================


def construir_dashboard_operativo(
    datos_en_vivo: dict,
    *,
    ultima_medicion=None,
) -> dict:

    disco = (
        datos_en_vivo.get(
            "disco",
            {},
        )
    )


    rutas_live = (
        datos_en_vivo.get(
            "rutas",
            [],
        )
    )


    (
        rutas_operativas,
        rutas_con_error,
    ) = _construir_rutas(
        rutas_live
    )


    porcentaje_usado = float(
        disco.get(
            "porcentaje_usado",
            0,
        )
        or 0
    )


    estado = (
        _estado_general(
            porcentaje_usado=(
                porcentaje_usado
            ),

            rutas_con_error=(
                rutas_con_error
            ),

            ultima_medicion=(
                ultima_medicion
            ),
        )
    )


    tipos_interes = (
        _construir_tipos_interes(
            rutas_live
        )
    )


    configuraciones = (
        RutaMonitoreada.objects
        .filter(
            activa=True,
            visible_dashboard=True,
        )
    )


    extensiones_interes = set()


    for configuracion in configuraciones:

        extensiones_interes.update(
            configuracion
            .extensiones_interes
            or []
        )


    principal_consumidor = (
        rutas_operativas[0]
        if rutas_operativas
        else None
    )


    return {
        "estado": estado,

        "rutas": (
            rutas_operativas
        ),

        "principales_consumidores": (
            rutas_operativas[:5]
        ),

        "principal_consumidor": (
            principal_consumidor
        ),

        "rutas_con_error": (
            rutas_con_error
        ),

        "tipos_interes": (
            tipos_interes
        ),

        "total_tipos_interes": len(
            tipos_interes
        ),

        "total_extensiones_interes": len(
            extensiones_interes
        ),
    }