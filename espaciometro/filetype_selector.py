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
# DEFINICIÓN DE TIPOS DISPONIBLES
# =============================================================================


TIPOS_ARCHIVO = [
    {
        "codigo": "imagen",
        "nombre": "Imágenes",
        "descripcion": (
            "Fotografías, capturas e imágenes "
            "utilizadas por el sistema."
        ),
        "extensiones": sorted(
            EXTENSIONES_IMAGEN
        ),
    },

    {
        "codigo": "pdf",
        "nombre": "PDF",
        "descripcion": (
            "Documentos PDF almacenados "
            "por el sistema."
        ),
        "extensiones": [
            ".pdf",
        ],
    },

    {
        "codigo": "documento",
        "nombre": "Documentos",
        "descripcion": (
            "Documentos de texto y archivos "
            "de oficina."
        ),
        "extensiones": sorted(
            EXTENSIONES_DOCUMENTO
        ),
    },

    {
        "codigo": "planilla",
        "nombre": "Planillas",
        "descripcion": (
            "Planillas y archivos tabulares."
        ),
        "extensiones": sorted(
            EXTENSIONES_PLANILLA
        ),
    },

    {
        "codigo": "video",
        "nombre": "Videos",
        "descripcion": (
            "Archivos de video."
        ),
        "extensiones": sorted(
            EXTENSIONES_VIDEO
        ),
    },

    {
        "codigo": "audio",
        "nombre": "Audio",
        "descripcion": (
            "Grabaciones y archivos de audio."
        ),
        "extensiones": sorted(
            EXTENSIONES_AUDIO
        ),
    },

    {
        "codigo": "comprimido",
        "nombre": "Comprimidos",
        "descripcion": (
            "ZIP, TAR, RAR y otros "
            "archivos comprimidos."
        ),
        "extensiones": sorted(
            EXTENSIONES_COMPRIMIDO
        ),
    },

    {
        "codigo": "temporal",
        "nombre": "Temporales",
        "descripcion": (
            "Archivos temporales o "
            "potencialmente prescindibles."
        ),
        "extensiones": sorted(
            EXTENSIONES_TEMPORAL
        ),
    },

    {
        "codigo": "base_datos",
        "nombre": "Bases de datos",
        "descripcion": (
            "Archivos físicos de base de datos."
        ),
        "extensiones": sorted(
            EXTENSIONES_BASE_DATOS
        ),
    },

    {
        "codigo": "codigo",
        "nombre": "Código fuente",
        "descripcion": (
            "Código y recursos utilizados "
            "por la aplicación."
        ),
        "extensiones": sorted(
            EXTENSIONES_CODIGO
        ),
    },

    {
        "codigo": "configuracion",
        "nombre": "Configuración",
        "descripcion": (
            "JSON, YAML, XML, INI y otros "
            "archivos de configuración."
        ),
        "extensiones": sorted(
            EXTENSIONES_CONFIGURACION
        ),
    },

    {
        "codigo": "otro",
        "nombre": "Otros",
        "descripcion": (
            "Archivos que no pertenecen "
            "a las categorías anteriores."
        ),
        "extensiones": [],
    },
]


# =============================================================================
# UTILIDADES
# =============================================================================


def _normalizar_extension(
    extension: str,
) -> str:

    extension = (
        str(extension)
        .strip()
        .lower()
    )

    if not extension:
        return ""

    if not extension.startswith("."):
        extension = "." + extension

    return extension


def _tipos_validos() -> set[str]:

    return {
        tipo["codigo"]
        for tipo in TIPOS_ARCHIVO
    }


def _extensiones_por_tipo() -> dict:

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
        }

    return resultado


# =============================================================================
# OBTENER CONFIGURACIÓN
# =============================================================================


def obtener_selector_tipos() -> dict:
    """
    Construye la información necesaria para ESP006.

    Solamente muestra RutaMonitoreada activas.

    Una lista vacía de tipos significa:
    sin prioridad especial.
    """

    rutas = (
        RutaMonitoreada.objects
        .filter(activa=True)
        .order_by("nombre")
    )

    resultado_rutas = []


    for ruta in rutas:

        tipos_seleccionados = set(
            ruta.tipos_interes
            or []
        )

        extensiones_seleccionadas = {
            _normalizar_extension(
                extension
            )
            for extension
            in (
                ruta.extensiones_interes
                or []
            )
            if extension
        }


        tipos = []


        for definicion in TIPOS_ARCHIVO:

            codigo = definicion[
                "codigo"
            ]

            extensiones = []


            for extension in definicion[
                "extensiones"
            ]:

                extension_normalizada = (
                    _normalizar_extension(
                        extension
                    )
                )

                extensiones.append(
                    {
                        "valor": (
                            extension_normalizada
                        ),

                        "seleccionada": (
                            extension_normalizada
                            in extensiones_seleccionadas
                        ),
                    }
                )


            tipos.append(
                {
                    "codigo": codigo,

                    "nombre": definicion[
                        "nombre"
                    ],

                    "descripcion": definicion[
                        "descripcion"
                    ],

                    "seleccionado": (
                        codigo
                        in tipos_seleccionados
                    ),

                    "extensiones": extensiones,
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

                "tipos": tipos,

                "total_tipos": len(
                    tipos_seleccionados
                ),

                "total_extensiones": len(
                    extensiones_seleccionadas
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
# GUARDAR CONFIGURACIÓN
# =============================================================================


def guardar_selector_tipos(
    post,
) -> dict:
    """
    Guarda tipos/extensiones de interés.

    No modifica archivos.
    No modifica patrones_incluir/excluir.
    No toca rutas inactivas.
    """

    tipos_validos = (
        _tipos_validos()
    )

    extensiones_por_tipo = (
        _extensiones_por_tipo()
    )


    actualizadas = 0

    sin_cambios = 0


    rutas = (
        RutaMonitoreada.objects
        .filter(activa=True)
        .order_by("nombre")
    )


    for ruta in rutas:

        # =============================================================
        # TIPOS
        # =============================================================

        tipos_seleccionados = set(
            post.getlist(
                f"tipos_{ruta.pk}"
            )
        )


        tipos_seleccionados &= (
            tipos_validos
        )


        # =============================================================
        # EXTENSIONES
        # =============================================================

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


        # Solamente admitimos extensiones
        # pertenecientes a categorías seleccionadas.

        extensiones_permitidas = set()


        for codigo in (
            tipos_seleccionados
        ):

            extensiones_permitidas |= (
                extensiones_por_tipo.get(
                    codigo,
                    set(),
                )
            )


        extensiones_seleccionadas = (
            extensiones_recibidas
            & extensiones_permitidas
        )


        nuevos_tipos = sorted(
            tipos_seleccionados
        )

        nuevas_extensiones = sorted(
            extensiones_seleccionadas
        )


        anteriores_tipos = sorted(
            ruta.tipos_interes
            or []
        )

        anteriores_extensiones = sorted(
            ruta.extensiones_interes
            or []
        )


        if (
            anteriores_tipos
            == nuevos_tipos
            and
            anteriores_extensiones
            == nuevas_extensiones
        ):

            sin_cambios += 1

            continue


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