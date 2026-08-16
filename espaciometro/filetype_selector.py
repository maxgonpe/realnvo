from __future__ import annotations

from .classifier import (
    EXTENSIONES_AUDIO,
    EXTENSIONES_BASE_DATOS,
    EXTENSIONES_CODIGO,
    EXTENSIONES_COMPRIMIDO,
    EXTENSIONES_CONFIGURACION,
    EXTENSIONES_DOCUMENTO,
    EXTENSIONES_IMAGEN,
    EXTENSIONES_PLANILLA,
    EXTENSIONES_TEMPORAL,
    EXTENSIONES_VIDEO,
)
from .models import RutaMonitoreada


# =============================================================================
# CATÁLOGO ESP006
# =============================================================================


TIPOS_ARCHIVO = (
    {
        "codigo": "imagen",
        "nombre": "Imágenes",
        "descripcion": (
            "Fotografías, capturas, firmas, evidencias "
            "y otras imágenes."
        ),
        "extensiones": EXTENSIONES_IMAGEN,
    },
    {
        "codigo": "pdf",
        "nombre": "PDF",
        "descripcion": (
            "Documentos y comprobantes almacenados "
            "en formato PDF."
        ),
        "extensiones": {".pdf"},
    },
    {
        "codigo": "documento",
        "nombre": "Documentos",
        "descripcion": (
            "Documentos de texto y formatos "
            "de oficina."
        ),
        "extensiones": EXTENSIONES_DOCUMENTO,
    },
    {
        "codigo": "planilla",
        "nombre": "Planillas",
        "descripcion": (
            "Planillas de cálculo y archivos "
            "tabulares."
        ),
        "extensiones": EXTENSIONES_PLANILLA,
    },
    {
        "codigo": "audio",
        "nombre": "Audio",
        "descripcion": (
            "Grabaciones y otros archivos "
            "de audio."
        ),
        "extensiones": EXTENSIONES_AUDIO,
    },
    {
        "codigo": "video",
        "nombre": "Videos",
        "descripcion": (
            "Grabaciones y archivos de video."
        ),
        "extensiones": EXTENSIONES_VIDEO,
    },
    {
        "codigo": "comprimido",
        "nombre": "Comprimidos",
        "descripcion": (
            "ZIP, TAR, RAR y otros paquetes "
            "comprimidos."
        ),
        "extensiones": EXTENSIONES_COMPRIMIDO,
    },
    {
        "codigo": "temporal",
        "nombre": "Temporales",
        "descripcion": (
            "Archivos temporales que podrán ser "
            "especialmente interesantes para "
            "mantenimiento futuro."
        ),
        "extensiones": EXTENSIONES_TEMPORAL,
    },
    {
        "codigo": "base_datos",
        "nombre": "Archivos de base de datos",
        "descripcion": (
            "SQLite y otros archivos físicos "
            "de base de datos."
        ),
        "extensiones": EXTENSIONES_BASE_DATOS,
    },
    {
        "codigo": "codigo",
        "nombre": "Código fuente",
        "descripcion": (
            "Python, JavaScript, CSS, HTML y "
            "otros archivos de programación."
        ),
        "extensiones": EXTENSIONES_CODIGO,
    },
    {
        "codigo": "configuracion",
        "nombre": "Configuración",
        "descripcion": (
            "JSON, YAML, XML, INI y otros "
            "archivos de configuración."
        ),
        "extensiones": EXTENSIONES_CONFIGURACION,
    },
    {
        "codigo": "otro",
        "nombre": "Otros",
        "descripcion": (
            "Archivos que no pertenecen a las "
            "categorías anteriores."
        ),
        "extensiones": set(),
    },
)


# =============================================================================
# UTILIDADES
# =============================================================================


def _normalizar_extension(extension: str) -> str:
    """
    Normaliza una extensión:

        JPG  -> .jpg
        .PDF -> .pdf
    """

    extension = str(
        extension or ""
    ).strip().lower()

    if not extension:
        return ""

    if not extension.startswith("."):
        extension = "." + extension

    return extension


def _lista_json(valor) -> list:
    """
    Garantiza una lista aunque un registro antiguo
    contenga None u otro valor inesperado.
    """

    if isinstance(valor, list):
        return valor

    if isinstance(valor, tuple):
        return list(valor)

    if isinstance(valor, set):
        return list(valor)

    return []


def _catalogo_tipos_validos() -> set[str]:

    return {
        tipo["codigo"]
        for tipo in TIPOS_ARCHIVO
    }


def _catalogo_extensiones() -> dict[str, set[str]]:
    """
    Devuelve:

        {
            "imagen": {".jpg", ".png", ...},
            "pdf": {".pdf"},
            ...
        }
    """

    resultado = {}

    for tipo in TIPOS_ARCHIVO:

        resultado[
            tipo["codigo"]
        ] = {
            _normalizar_extension(
                extension
            )
            for extension
            in tipo["extensiones"]
            if extension
        }

    return resultado


# =============================================================================
# SELECTOR
# =============================================================================


def obtener_selector_tipos() -> dict:
    """
    Obtiene la configuración ESP006 para todas
    las RutaMonitoreada activas.

    No modifica datos.
    """

    rutas = (
        RutaMonitoreada.objects
        .filter(activa=True)
        .order_by("nombre")
    )

    resultado_rutas = []


    for ruta in rutas:

        tipos_guardados = set(
            _lista_json(
                ruta.tipos_interes
            )
        )

        extensiones_guardadas = {
            _normalizar_extension(
                extension
            )
            for extension
            in _lista_json(
                ruta.extensiones_interes
            )
            if extension
        }


        tipos_resultado = []


        for tipo in TIPOS_ARCHIVO:

            codigo = tipo[
                "codigo"
            ]


            extensiones_resultado = []


            for extension in sorted(
                tipo["extensiones"]
            ):

                extension = (
                    _normalizar_extension(
                        extension
                    )
                )

                extensiones_resultado.append(
                    {
                        "valor": extension,

                        "seleccionada": (
                            extension
                            in extensiones_guardadas
                        ),
                    }
                )


            tipos_resultado.append(
                {
                    "codigo": codigo,

                    "nombre": tipo[
                        "nombre"
                    ],

                    "descripcion": tipo[
                        "descripcion"
                    ],

                    "seleccionado": (
                        codigo
                        in tipos_guardados
                    ),

                    "extensiones": (
                        extensiones_resultado
                    ),
                }
            )


        resultado_rutas.append(
            {
                "id": ruta.pk,

                "nombre": ruta.nombre,

                "ruta": ruta.ruta,

                "categoria": (
                    ruta.get_categoria_display()
                ),

                "tipos": (
                    tipos_resultado
                ),

                "total_tipos": len(
                    tipos_guardados
                ),

                "total_extensiones": len(
                    extensiones_guardadas
                ),
            }
        )


    return {
        "rutas": resultado_rutas,

        "total_rutas": len(
            resultado_rutas
        ),
    }


# =============================================================================
# GUARDAR
# =============================================================================


def guardar_selector_tipos(post) -> dict:
    """
    Guarda la configuración ESP006.

    Reglas:

    - solamente trabaja sobre rutas activas;
    - no modifica patrones_incluir;
    - no modifica patrones_excluir;
    - no modifica archivos físicos;
    - no concede permisos de mantenimiento.
    """

    tipos_validos = (
        _catalogo_tipos_validos()
    )

    catalogo_extensiones = (
        _catalogo_extensiones()
    )


    actualizadas = 0

    sin_cambios = 0


    rutas = (
        RutaMonitoreada.objects
        .filter(activa=True)
        .order_by("nombre")
    )


    for ruta in rutas:

        # =====================================================================
        # TIPOS SELECCIONADOS
        # =====================================================================

        tipos_recibidos = set(
            post.getlist(
                f"tipos_{ruta.pk}"
            )
        )


        tipos_seleccionados = (
            tipos_recibidos
            & tipos_validos
        )


        # =====================================================================
        # EXTENSIONES RECIBIDAS
        # =====================================================================

        extensiones_recibidas = {
            _normalizar_extension(
                extension
            )
            for extension
            in post.getlist(
                f"extensiones_{ruta.pk}"
            )
            if extension
        }


        # =====================================================================
        # EXTENSIONES PERMITIDAS
        # =====================================================================
        #
        # Solo se conservan extensiones pertenecientes
        # a categorías que están seleccionadas.
        # =====================================================================

        extensiones_permitidas = set()


        for codigo in tipos_seleccionados:

            extensiones_permitidas |= (
                catalogo_extensiones.get(
                    codigo,
                    set(),
                )
            )


        extensiones_seleccionadas = (
            extensiones_recibidas
            & extensiones_permitidas
        )


        # =====================================================================
        # NORMALIZAR PARA JSON
        # =====================================================================

        nuevos_tipos = sorted(
            tipos_seleccionados
        )


        nuevas_extensiones = sorted(
            extensiones_seleccionadas
        )


        anteriores_tipos = sorted(
            _lista_json(
                ruta.tipos_interes
            )
        )


        anteriores_extensiones = sorted(
            _normalizar_extension(
                extension
            )
            for extension
            in _lista_json(
                ruta.extensiones_interes
            )
            if extension
        )


        # =====================================================================
        # SIN CAMBIOS
        # =====================================================================

        if (
            anteriores_tipos
            == nuevos_tipos
            and
            anteriores_extensiones
            == nuevas_extensiones
        ):

            sin_cambios += 1

            continue


        # =====================================================================
        # GUARDAR
        # =====================================================================

        ruta.tipos_interes = (
            nuevos_tipos
        )

        ruta.extensiones_interes = (
            nuevas_extensiones
        )


        ruta.save(
            update_fields=[
                "tipos_interes",
                "extensiones_interes",
            ]
        )


        actualizadas += 1


    return {
        "actualizadas": actualizadas,

        "sin_cambios": sin_cambios,
    }