from __future__ import annotations

from pathlib import Path

from django.db import connection

from .models import bytes_legibles


# =============================================================================
# ESP020 — INVENTARIO DE BASE DE DATOS
# =============================================================================
#
# PRINCIPIOS:
#
# - Solo lectura.
# - No importa modelos de otras aplicaciones.
# - No utiliza ForeignKey hacia tablas externas.
# - No ejecuta INSERT / UPDATE / DELETE / ALTER.
# - No interpreta reglas de negocio.
#
# Espaciómetro observa la base mediante introspección SQL/Django.
# =============================================================================


TIPOS_TEMPORALES = {
    "DateField",
    "DateTimeField",
}


def _nombre_motor():

    vendor = (
        connection.vendor
        or ""
    ).lower()


    nombres = {
        "sqlite": "SQLite",
        "postgresql": "PostgreSQL",
        "mysql": "MySQL / MariaDB",
        "oracle": "Oracle",
    }


    return nombres.get(
        vendor,
        vendor or "Desconocido",
    )


def _clasificar_tabla(
    nombre,
):

    nombre = str(
        nombre
        or ""
    )


    if nombre.startswith(
        "esp_"
    ):

        return {
            "codigo": "ESPACIOMETRO",
            "nombre": "Espaciómetro",
        }


    if (
        nombre.startswith(
            "django_"
        )
        or
        nombre.startswith(
            "auth_"
        )
    ):

        return {
            "codigo": "DJANGO",
            "nombre": "Sistema Django",
        }


    return {
        "codigo": "PROYECTO",
        "nombre": "Aplicación / proyecto",
    }


# =============================================================================
# INFORMACIÓN DE LA BASE
# =============================================================================


def _nombre_base_datos():

    if (
        connection.vendor
        == "sqlite"
    ):

        nombre = (
            connection
            .settings_dict
            .get(
                "NAME"
            )
        )


        return str(
            nombre
            or ""
        )


    try:

        with connection.cursor() as cursor:

            if (
                connection.vendor
                == "postgresql"
            ):

                cursor.execute(
                    "SELECT current_database()"
                )

                fila = cursor.fetchone()

                return (
                    fila[0]
                    if fila
                    else ""
                )


    except Exception:

        pass


    return str(
        connection
        .settings_dict
        .get(
            "NAME",
            "",
        )
    )


def _tamano_base_datos():

    # =========================================================================
    # SQLITE
    # =========================================================================

    if (
        connection.vendor
        == "sqlite"
    ):

        nombre = (
            connection
            .settings_dict
            .get(
                "NAME"
            )
        )


        if not nombre:

            return None


        if str(
            nombre
        ) == ":memory:":

            return None


        try:

            path = Path(
                nombre
            )


            if (
                path.exists()
                and path.is_file()
            ):

                return int(
                    path.stat().st_size
                )


        except (
            OSError,
            TypeError,
            ValueError,
        ):

            return None


    # =========================================================================
    # POSTGRESQL
    # =========================================================================

    if (
        connection.vendor
        == "postgresql"
    ):

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        pg_database_size(
                            current_database()
                        )
                    """
                )


                fila = cursor.fetchone()


                if fila:

                    return int(
                        fila[0]
                        or 0
                    )


        except Exception:

            return None


    return None


# =============================================================================
# COLUMNAS
# =============================================================================


def _columnas_tabla(
    cursor,
    tabla,
):

    columnas = []

    temporales = []


    try:

        descripcion = (
            connection
            .introspection
            .get_table_description(
                cursor,
                tabla,
            )
        )


    except Exception as exc:

        return {
            "columnas": [],
            "temporales": [],
            "error": str(
                exc
            ),
        }


    for campo in descripcion:

        nombre = str(
            campo.name
        )


        try:

            tipo_django = (
                connection
                .introspection
                .get_field_type(
                    campo.type_code,
                    campo,
                )
            )


        except Exception:

            tipo_django = str(
                campo.type_code
            )


        columna = {
            "nombre": nombre,

            "tipo": (
                tipo_django
                or ""
            ),

            "permite_null": (
                getattr(
                    campo,
                    "null_ok",
                    None,
                )
            ),

            "temporal": (
                tipo_django
                in TIPOS_TEMPORALES
            ),
        }


        columnas.append(
            columna
        )


        if columna[
            "temporal"
        ]:

            temporales.append(
                columna
            )


    return {
        "columnas": columnas,

        "temporales": temporales,

        "error": "",
    }


# =============================================================================
# CONTEO
# =============================================================================


def _contar_registros(
    cursor,
    tabla,
):

    nombre_seguro = (
        connection
        .ops
        .quote_name(
            tabla
        )
    )


    cursor.execute(
        f"SELECT COUNT(*) FROM {nombre_seguro}"
    )


    fila = cursor.fetchone()


    return int(
        fila[0]
        if fila
        else 0
    )


# =============================================================================
# INVENTARIO PRINCIPAL
# =============================================================================


def inspeccionar_base_datos(
    *,
    contar_registros=False,
):
    """
    Inspección genérica de la base activa configurada
    en Django.

    No importa modelos del proyecto y no modifica datos.
    """

    connection.ensure_connection()


    tamano_bd = (
        _tamano_base_datos()
    )


    resultado = {
        "motor": (
            _nombre_motor()
        ),

        "vendor": (
            connection.vendor
        ),

        "nombre_base": (
            _nombre_base_datos()
        ),

        "tamano_bytes": (
            tamano_bd
            or 0
        ),

        "tamano_legible": (
            bytes_legibles(
                tamano_bd
                or 0
            )
            if tamano_bd
            else "-"
        ),

        "contando": bool(
            contar_registros
        ),

        "tablas": [],

        "total_tablas": 0,

        "total_registros": 0,

        "total_columnas_temporales": 0,

        "errores": [],
    }


    try:

        with connection.cursor() as cursor:

            tablas = (
                connection
                .introspection
                .table_names(
                    cursor
                )
            )


            tablas = sorted(
                tablas
            )


            for tabla in tablas:

                clasificacion = (
                    _clasificar_tabla(
                        tabla
                    )
                )


                estructura = (
                    _columnas_tabla(
                        cursor,
                        tabla,
                    )
                )


                cantidad = None

                error_conteo = ""


                if contar_registros:

                    try:

                        cantidad = (
                            _contar_registros(
                                cursor,
                                tabla,
                            )
                        )


                    except Exception as exc:

                        error_conteo = str(
                            exc
                        )


                item = {
                    "nombre": tabla,

                    "clasificacion": (
                        clasificacion
                    ),

                    "columnas": (
                        estructura[
                            "columnas"
                        ]
                    ),

                    "columnas_total": len(
                        estructura[
                            "columnas"
                        ]
                    ),

                    "temporales": (
                        estructura[
                            "temporales"
                        ]
                    ),

                    "temporales_total": len(
                        estructura[
                            "temporales"
                        ]
                    ),

                    "registros": cantidad,

                    "error": (
                        estructura[
                            "error"
                        ]
                        or error_conteo
                    ),
                }


                resultado[
                    "tablas"
                ].append(
                    item
                )


                resultado[
                    "total_columnas_temporales"
                ] += (
                    item[
                        "temporales_total"
                    ]
                )


                if (
                    cantidad
                    is not None
                ):

                    resultado[
                        "total_registros"
                    ] += cantidad


    except Exception as exc:

        resultado[
            "errores"
        ].append(
            str(
                exc
            )
        )


    resultado[
        "total_tablas"
    ] = len(
        resultado[
            "tablas"
        ]
    )


    return resultado