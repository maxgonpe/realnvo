from __future__ import annotations

from pathlib import Path

from django.db import connections

from .models import bytes_legibles


# =============================================================================
# ESP020 / ESP021 — INVENTARIO DE BASE DE DATOS
# =============================================================================
#
# PRINCIPIOS:
#
# - Solo lectura.
# - No importa modelos de otras aplicaciones.
# - No utiliza ForeignKey hacia tablas externas.
# - No ejecuta INSERT / UPDATE / DELETE / ALTER.
# - No interpreta reglas de negocio.
# - Puede inspeccionar cualquier conexión declarada en DATABASES.
#
# Espaciómetro observa la base mediante introspección SQL/Django.
# =============================================================================


TIPOS_TEMPORALES = {
    "DateField",
    "DateTimeField",
}


# =============================================================================
# MOTOR
# =============================================================================


def _nombre_motor(
    db_connection,
):

    vendor = (
        db_connection.vendor
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


def _nombre_base_datos(
    db_connection,
):

    if (
        db_connection.vendor
        == "sqlite"
    ):

        nombre = (
            db_connection
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

        with db_connection.cursor() as cursor:

            if (
                db_connection.vendor
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
        db_connection
        .settings_dict
        .get(
            "NAME",
            "",
        )
    )


def _tamano_base_datos(
    db_connection,
):

    # =========================================================================
    # SQLITE
    # =========================================================================

    if (
        db_connection.vendor
        == "sqlite"
    ):

        nombre = (
            db_connection
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
        db_connection.vendor
        == "postgresql"
    ):

        try:

            with db_connection.cursor() as cursor:

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
    db_connection,
    cursor,
    tabla,
):

    columnas = []

    temporales = []


    try:

        descripcion = (
            db_connection
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
                db_connection
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
    db_connection,
    cursor,
    tabla,
):

    nombre_seguro = (
        db_connection
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
    alias="default",
    contar_registros=False,
):
    """
    Inspección genérica de una conexión configurada
    en Django.

    Por compatibilidad, si no se indica alias utiliza
    la conexión "default".

    No importa modelos del proyecto y no modifica datos.
    """

    db_connection = (
        connections[
            alias
        ]
    )


    db_connection.ensure_connection()


    tamano_bd = (
        _tamano_base_datos(
            db_connection
        )
    )


    resultado = {
        "alias": alias,

        "motor": (
            _nombre_motor(
                db_connection
            )
        ),

        "vendor": (
            db_connection.vendor
        ),

        "nombre_base": (
            _nombre_base_datos(
                db_connection
            )
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

        with db_connection.cursor() as cursor:

            tablas = (
                db_connection
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
                        db_connection,
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
                                db_connection,
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