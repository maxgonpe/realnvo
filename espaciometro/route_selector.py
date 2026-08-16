from __future__ import annotations

import hashlib
from pathlib import Path

from django.conf import settings

from .models import RutaMonitoreada
from .structure import analizar_estructura_proyecto


# =============================================================================
# UTILIDADES
# =============================================================================


def _resolver_ruta_modelo(
    ruta_monitoreada: RutaMonitoreada,
) -> Path:
    """
    Obtiene la ruta física real correspondiente
    a una RutaMonitoreada.
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


def _form_id(
    ruta_relativa: str,
) -> str:
    """
    Genera un identificador seguro para usar
    en los nombres de campos HTML.
    """

    return hashlib.sha1(
        ruta_relativa.encode("utf-8")
    ).hexdigest()[:12]


def _categoria_sugerida(
    ruta_fisica: Path,
) -> str:
    """
    Sugiere una categoría utilizando solamente
    configuración estándar de Django.

    No conoce ninguna app del proyecto anfitrión.
    """

    try:

        # =============================================================
        # MEDIA_ROOT
        # =============================================================

        media_root = getattr(
            settings,
            "MEDIA_ROOT",
            "",
        )

        if media_root:

            media_path = Path(
                media_root
            ).expanduser().resolve(
                strict=False
            )

            if ruta_fisica == media_path:

                return (
                    RutaMonitoreada
                    .Categoria
                    .MEDIA
                )


        # =============================================================
        # STATIC_ROOT
        # =============================================================

        static_root = getattr(
            settings,
            "STATIC_ROOT",
            "",
        )

        if static_root:

            static_path = Path(
                static_root
            ).expanduser().resolve(
                strict=False
            )

            if ruta_fisica == static_path:

                return (
                    RutaMonitoreada
                    .Categoria
                    .REGENERABLE
                )


    except (
        TypeError,
        ValueError,
        OSError,
    ):
        pass


    return (
        RutaMonitoreada
        .Categoria
        .OTRO
    )


def _nombre_unico(
    nombre_base: str,
) -> str:
    """
    Crea un nombre único para RutaMonitoreada.
    """

    nombre = nombre_base

    numero = 2


    while RutaMonitoreada.objects.filter(
        nombre=nombre
    ).exists():

        nombre = (
            f"{nombre_base} ({numero})"
        )

        numero += 1


    return nombre


def _buscar_registro_por_ruta(
    ruta_fisica: Path,
) -> RutaMonitoreada | None:
    """
    Busca una RutaMonitoreada mediante su ruta física resuelta.

    Así podemos comparar tanto rutas relativas como absolutas.
    """

    for registro in (
        RutaMonitoreada.objects.all()
    ):

        try:

            if (
                _resolver_ruta_modelo(
                    registro
                )
                == ruta_fisica
            ):

                return registro

        except Exception:
            continue


    return None


# =============================================================================
# OBTENER SELECTOR
# =============================================================================


def obtener_selector_rutas() -> dict:
    """
    Combina:

    - directorios descubiertos por ESP002;
    - configuraciones existentes en RutaMonitoreada.

    Esta función es solamente de lectura.
    """

    estructura = (
        analizar_estructura_proyecto()
    )


    resultado = {

        "base_dir": estructura.get(
            "base_dir",
            "",
        ),

        "error": estructura.get(
            "error",
            "",
        ),

        "rutas": [],

        "categorias": list(
            RutaMonitoreada
            .Categoria
            .choices
        ),
    }


    if resultado["error"]:
        return resultado


    base_dir = Path(
        settings.BASE_DIR
    ).expanduser().resolve(
        strict=False
    )


    # =========================================================================
    # CONSTRUIR ÍNDICE DE RUTAS EXISTENTES
    # =========================================================================

    existentes_por_path = {}


    for registro in (
        RutaMonitoreada.objects.all()
    ):

        try:

            path = (
                _resolver_ruta_modelo(
                    registro
                )
            )

            existentes_por_path[
                str(path)
            ] = registro

        except Exception:
            continue


    # =========================================================================
    # DIRECTORIOS DESCUBIERTOS
    # =========================================================================

    for directorio in estructura[
        "directorios"
    ]:

        path = Path(
            directorio["ruta"]
        ).resolve(
            strict=False
        )


        try:

            ruta_relativa = str(
                path.relative_to(
                    base_dir
                )
            )

        except ValueError:
            continue


        existente = (
            existentes_por_path.get(
                str(path)
            )
        )


        # =====================================================================
        # YA ESTÁ CONFIGURADA
        # =====================================================================

        if existente:

            categoria = (
                existente.categoria
            )

            activa = (
                existente.activa
            )

            registrada = True

            nombre_configurado = (
                existente.nombre
            )

            permite_mantenimiento = (
                existente
                .permite_mantenimiento
            )


        # =====================================================================
        # TODAVÍA NO ESTÁ CONFIGURADA
        # =====================================================================

        else:

            categoria = (
                _categoria_sugerida(
                    path
                )
            )

            activa = False

            registrada = False

            nombre_configurado = ""

            permite_mantenimiento = False


        resultado["rutas"].append(
            {

                "form_id": _form_id(
                    ruta_relativa
                ),

                "nombre": directorio[
                    "nombre"
                ],

                "ruta_relativa": (
                    ruta_relativa
                ),

                "ruta_absoluta": str(
                    path
                ),

                "total_bytes": directorio[
                    "total_bytes"
                ],

                "total_legible": directorio[
                    "total_legible"
                ],

                "total_archivos": directorio[
                    "total_archivos"
                ],

                "total_directorios": directorio[
                    "total_directorios"
                ],

                "tipo_principal": (
                    directorio.get(
                        "tipo_principal"
                    )
                ),

                "categoria": categoria,

                "activa": activa,

                "registrada": registrada,

                "nombre_configurado": (
                    nombre_configurado
                ),

                "permite_mantenimiento": (
                    permite_mantenimiento
                ),
            }
        )


    return resultado


# =============================================================================
# GUARDAR SELECCIÓN
# =============================================================================


def guardar_seleccion_rutas(
    post,
) -> dict:
    """
    Guarda la selección de rutas realizada desde ESP005.

    REGLAS:

    - una ruta marcada se crea o activa;
    - una ruta desmarcada se desactiva;
    - nunca se elimina RutaMonitoreada;
    - nunca se borran mediciones históricas;
    - nunca se habilita mantenimiento automáticamente;
    - nunca se modifican archivos físicos.
    """

    selector = (
        obtener_selector_rutas()
    )


    if selector["error"]:

        return {

            "creadas": 0,

            "activadas": 0,

            "desactivadas": 0,

            "actualizadas": 0,

            "error": selector["error"],
        }


    # =========================================================================
    # RUTAS MARCADAS POR EL USUARIO
    # =========================================================================

    seleccionadas = set(
        post.getlist(
            "monitorizar"
        )
    )


    categorias_validas = {

        valor

        for valor, etiqueta

        in (
            RutaMonitoreada
            .Categoria
            .choices
        )
    }


    creadas = 0

    activadas = 0

    desactivadas = 0

    actualizadas = 0


    # =========================================================================
    # PROCESAR TODAS LAS RUTAS DESCUBIERTAS
    # =========================================================================

    for fila in selector[
        "rutas"
    ]:

        ruta_relativa = fila[
            "ruta_relativa"
        ]


        seleccionada = (
            ruta_relativa
            in seleccionadas
        )


        # =====================================================================
        # CATEGORÍA ELEGIDA
        # =====================================================================

        categoria = post.get(

            (
                "categoria_"
                f"{fila['form_id']}"
            ),

            fila["categoria"],
        )


        if (
            categoria
            not in categorias_validas
        ):

            categoria = (
                RutaMonitoreada
                .Categoria
                .OTRO
            )


        # =====================================================================
        # BUSCAR CONFIGURACIÓN EXISTENTE
        # =====================================================================

        ruta_fisica = Path(
            fila["ruta_absoluta"]
        ).resolve(
            strict=False
        )


        registro = (
            _buscar_registro_por_ruta(
                ruta_fisica
            )
        )


        # =====================================================================
        # RUTA MARCADA
        # =====================================================================

        if seleccionada:

            # -----------------------------------------------------------------
            # NUEVA
            # -----------------------------------------------------------------

            if registro is None:

                nombre = _nombre_unico(
                    fila["nombre"]
                )


                RutaMonitoreada.objects.create(

                    nombre=nombre,

                    ruta=ruta_relativa,

                    relativa_a_base_dir=True,

                    categoria=categoria,

                    recursiva=True,

                    seguir_enlaces_simbolicos=False,

                    patrones_incluir=[],

                    patrones_excluir=[],

                    activa=True,

                    visible_dashboard=True,

                    # ---------------------------------------------------------
                    # SEGURIDAD
                    # ---------------------------------------------------------
                    # Monitorizar NO significa autorizar eliminación.
                    # ---------------------------------------------------------

                    permite_mantenimiento=False,

                    observaciones=(
                        "Ruta configurada "
                        "mediante ESP005."
                    ),
                )


                creadas += 1


            # -----------------------------------------------------------------
            # YA EXISTE
            # -----------------------------------------------------------------

            else:

                estaba_activa = (
                    registro.activa
                )


                hubo_cambio = False


                if not registro.activa:

                    registro.activa = True

                    activadas += 1

                    hubo_cambio = True


                if (
                    registro.categoria
                    != categoria
                ):

                    registro.categoria = (
                        categoria
                    )

                    hubo_cambio = True


                if hubo_cambio:

                    # =========================================================
                    # IMPORTANTE:
                    #
                    # No utilizamos update_fields con nombres de timestamps.
                    # De esta forma ESP005 no depende de que el modelo tenga
                    # un campo llamado actualizado_en, actualizado, modified,
                    # etc.
                    # =========================================================

                    registro.save()

                    actualizadas += 1


        # =====================================================================
        # RUTA DESMARCADA
        # =====================================================================

        else:

            if (
                registro is not None
                and registro.activa
            ):

                registro.activa = False

                # Mismo principio:
                # guardamos el modelo sin asumir
                # la existencia de campos adicionales.

                registro.save()

                desactivadas += 1


    return {

        "creadas": creadas,

        "activadas": activadas,

        "desactivadas": desactivadas,

        "actualizadas": actualizadas,

        "error": "",
    }