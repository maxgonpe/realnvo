from __future__ import annotations

import hashlib
import os
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
    Obtiene la ruta física correspondiente a una RutaMonitoreada.

    Puede trabajar tanto con rutas relativas a BASE_DIR
    como con rutas absolutas.
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
    valor: str,
) -> str:
    """
    Genera un identificador seguro y estable
    para los controles HTML.
    """

    return hashlib.sha1(
        valor.encode("utf-8")
    ).hexdigest()[:12]


def _categoria_sugerida(
    ruta_fisica: Path,
) -> str:
    """
    Sugiere categoría utilizando únicamente
    configuraciones estándar de Django.

    No conoce ninguna aplicación del proyecto anfitrión.
    """

    try:

        # =====================================================================
        # MEDIA_ROOT
        # =====================================================================

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


        # =====================================================================
        # STATIC_ROOT
        # =====================================================================

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
    Genera un nombre único para RutaMonitoreada.
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


def _estado_fisico(
    ruta: Path,
) -> dict:
    """
    Comprueba el estado real de una ruta configurada.

    Importante:
    esta función solamente consulta el filesystem.
    """

    try:

        existe = ruta.exists()

    except OSError:

        existe = False


    if not existe:

        return {
            "existe": False,
            "es_directorio": False,
            "lectura": False,
            "estado": "NO_EXISTE",
            "estado_texto": "No existe",
            "problema": True,
        }


    try:

        es_directorio = (
            ruta.is_dir()
        )

    except OSError:

        es_directorio = False


    if not es_directorio:

        return {
            "existe": True,
            "es_directorio": False,
            "lectura": False,
            "estado": "NO_DIRECTORIO",
            "estado_texto": (
                "Existe, pero no es directorio"
            ),
            "problema": True,
        }


    try:

        lectura = os.access(
            ruta,
            os.R_OK,
        )

    except OSError:

        lectura = False


    if not lectura:

        return {
            "existe": True,
            "es_directorio": True,
            "lectura": False,
            "estado": "SIN_LECTURA",
            "estado_texto": (
                "Existe, sin permiso de lectura"
            ),
            "problema": True,
        }


    return {
        "existe": True,
        "es_directorio": True,
        "lectura": True,
        "estado": "OK",
        "estado_texto": "Disponible",
        "problema": False,
    }


def _crear_fila_registrada(
    registro: RutaMonitoreada,
    *,
    descubierta: bool,
    datos_directorio: dict | None = None,
) -> dict:
    """
    Convierte una RutaMonitoreada existente
    en una fila del selector ESP005.
    """

    ruta_fisica = (
        _resolver_ruta_modelo(
            registro
        )
    )

    fisico = (
        _estado_fisico(
            ruta_fisica
        )
    )


    if datos_directorio:

        total_bytes = datos_directorio.get(
            "total_bytes",
            0,
        )

        total_legible = datos_directorio.get(
            "total_legible",
            "0 B",
        )

        total_archivos = datos_directorio.get(
            "total_archivos",
            0,
        )

        total_directorios = datos_directorio.get(
            "total_directorios",
            0,
        )

        tipo_principal = datos_directorio.get(
            "tipo_principal"
        )

    else:

        total_bytes = 0

        total_legible = "-"

        total_archivos = None

        total_directorios = None

        tipo_principal = None


    selector_key = (
        f"registro:{registro.pk}"
    )


    return {
        "selector_key": selector_key,

        "form_id": _form_id(
            selector_key
        ),

        "registro_id": registro.pk,

        "nombre": registro.nombre,

        "ruta_relativa": registro.ruta,

        "ruta_absoluta": str(
            ruta_fisica
        ),

        "total_bytes": total_bytes,

        "total_legible": total_legible,

        "total_archivos": (
            total_archivos
        ),

        "total_directorios": (
            total_directorios
        ),

        "tipo_principal": (
            tipo_principal
        ),

        "categoria": (
            registro.categoria
        ),

        "activa": (
            registro.activa
        ),

        "registrada": True,

        "nombre_configurado": (
            registro.nombre
        ),

        "permite_mantenimiento": (
            registro
            .permite_mantenimiento
        ),

        "descubierta": descubierta,

        "existe": fisico[
            "existe"
        ],

        "es_directorio": fisico[
            "es_directorio"
        ],

        "lectura": fisico[
            "lectura"
        ],

        "estado_fisico": fisico[
            "estado"
        ],

        "estado_fisico_texto": fisico[
            "estado_texto"
        ],

        "problema_fisico": fisico[
            "problema"
        ],
    }


def _crear_fila_nueva(
    directorio: dict,
    base_dir: Path,
) -> dict | None:
    """
    Construye una fila para un directorio descubierto
    que todavía no posee RutaMonitoreada.
    """

    ruta_fisica = Path(
        directorio["ruta"]
    ).resolve(
        strict=False
    )


    try:

        ruta_relativa = str(
            ruta_fisica.relative_to(
                base_dir
            )
        )

    except ValueError:

        return None


    selector_key = (
        f"nueva:{ruta_relativa}"
    )


    fisico = (
        _estado_fisico(
            ruta_fisica
        )
    )


    return {
        "selector_key": selector_key,

        "form_id": _form_id(
            selector_key
        ),

        "registro_id": None,

        "nombre": directorio[
            "nombre"
        ],

        "ruta_relativa": (
            ruta_relativa
        ),

        "ruta_absoluta": str(
            ruta_fisica
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

        "categoria": (
            _categoria_sugerida(
                ruta_fisica
            )
        ),

        "activa": False,

        "registrada": False,

        "nombre_configurado": "",

        "permite_mantenimiento": False,

        "descubierta": True,

        "existe": fisico[
            "existe"
        ],

        "es_directorio": fisico[
            "es_directorio"
        ],

        "lectura": fisico[
            "lectura"
        ],

        "estado_fisico": fisico[
            "estado"
        ],

        "estado_fisico_texto": fisico[
            "estado_texto"
        ],

        "problema_fisico": fisico[
            "problema"
        ],
    }


# =============================================================================
# OBTENER SELECTOR
# =============================================================================


def obtener_selector_rutas() -> dict:
    """
    ESP005.

    Combina dos fuentes:

    1. directorios descubiertos físicamente por ESP002;
    2. configuraciones RutaMonitoreada existentes en la BD.

    Esto permite detectar configuraciones heredadas cuya
    ruta física ya no existe en el servidor actual.
    """

    estructura = (
        analizar_estructura_proyecto()
    )


    base_dir = Path(
        settings.BASE_DIR
    ).expanduser().resolve(
        strict=False
    )


    registros = list(
        RutaMonitoreada.objects
        .all()
        .order_by("nombre")
    )


    # =========================================================================
    # ÍNDICE DE CONFIGURACIONES EXISTENTES POR RUTA FÍSICA
    # =========================================================================

    registros_por_path = {}


    for registro in registros:

        try:

            ruta_fisica = (
                _resolver_ruta_modelo(
                    registro
                )
            )

            registros_por_path.setdefault(
                str(ruta_fisica),
                [],
            ).append(
                registro
            )

        except Exception:

            continue


    filas = []

    ids_utilizados = set()


    # =========================================================================
    # 1. DIRECTORIOS DESCUBIERTOS
    # =========================================================================

    if not estructura.get(
        "error"
    ):

        for directorio in estructura.get(
            "directorios",
            [],
        ):

            ruta_fisica = Path(
                directorio["ruta"]
            ).resolve(
                strict=False
            )


            coincidencias = (
                registros_por_path.get(
                    str(ruta_fisica),
                    [],
                )
            )


            # -----------------------------------------------------------------
            # YA EXISTE UNA CONFIGURACIÓN PARA ESTA RUTA
            # -----------------------------------------------------------------

            if coincidencias:

                registro = coincidencias[0]

                ids_utilizados.add(
                    registro.pk
                )

                fila = (
                    _crear_fila_registrada(
                        registro,
                        descubierta=True,
                        datos_directorio=directorio,
                    )
                )

                filas.append(
                    fila
                )


            # -----------------------------------------------------------------
            # DIRECTORIO NUEVO
            # -----------------------------------------------------------------

            else:

                fila = (
                    _crear_fila_nueva(
                        directorio,
                        base_dir,
                    )
                )

                if fila is not None:

                    filas.append(
                        fila
                    )


    # =========================================================================
    # 2. CONFIGURACIONES QUE ESP002 NO DESCUBRIÓ
    # =========================================================================
    #
    # Este bloque resuelve precisamente el caso:
    #
    #   desarrollo:  /home/max/realnvo/otros       existe
    #   producción:  /home/max/myproject/otros     no existe
    #
    # El registro sigue apareciendo para que el usuario pueda desactivarlo.
    # =========================================================================

    for registro in registros:

        if registro.pk in ids_utilizados:

            continue


        fila = (
            _crear_fila_registrada(
                registro,
                descubierta=False,
                datos_directorio=None,
            )
        )


        filas.append(
            fila
        )


    # =========================================================================
    # ORDEN
    # =========================================================================
    #
    # Primero mostramos configuraciones problemáticas,
    # después el resto ordenado por tamaño.
    # =========================================================================

    filas.sort(
        key=lambda item: (
            0
            if item["problema_fisico"]
            else 1,

            -item["total_bytes"],

            item["nombre"].lower(),
        )
    )


    total_problematicas = sum(
        1
        for fila in filas
        if fila["problema_fisico"]
    )


    total_registradas = sum(
        1
        for fila in filas
        if fila["registrada"]
    )


    total_activas = sum(
        1
        for fila in filas
        if fila["registrada"]
        and fila["activa"]
    )


    return {
        "base_dir": str(
            base_dir
        ),

        "error_descubrimiento": (
            estructura.get(
                "error",
                "",
            )
        ),

        "rutas": filas,

        "categorias": list(
            RutaMonitoreada
            .Categoria
            .choices
        ),

        "total_rutas": len(
            filas
        ),

        "total_registradas": (
            total_registradas
        ),

        "total_activas": (
            total_activas
        ),

        "total_problematicas": (
            total_problematicas
        ),
    }


# =============================================================================
# GUARDAR SELECCIÓN
# =============================================================================


def guardar_seleccion_rutas(
    post,
) -> dict:
    """
    Guarda la selección ESP005.

    REGLAS:

    - una ruta marcada se crea o activa;
    - una ruta desmarcada se desactiva;
    - una ruta inexistente puede ser desactivada;
    - nunca se elimina RutaMonitoreada;
    - nunca se elimina su histórico;
    - nunca se habilita mantenimiento automáticamente;
    - nunca se crean directorios físicos;
    - nunca se mueven ni eliminan archivos.
    """

    selector = (
        obtener_selector_rutas()
    )


    # Si ni siquiera tenemos filas que administrar
    # y además falló el descubrimiento, no hay nada
    # seguro que podamos procesar.

    if (
        selector[
            "error_descubrimiento"
        ]
        and
        not selector["rutas"]
    ):

        return {
            "creadas": 0,
            "activadas": 0,
            "desactivadas": 0,
            "actualizadas": 0,
            "activas_sin_ruta": 0,
            "error": (
                selector[
                    "error_descubrimiento"
                ]
            ),
        }


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

    activas_sin_ruta = 0


    # =========================================================================
    # PROCESAR CADA FILA
    # =========================================================================

    for fila in selector[
        "rutas"
    ]:

        seleccionada = (
            fila["selector_key"]
            in seleccionadas
        )


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
        # CONFIGURACIÓN YA REGISTRADA
        # =====================================================================

        if fila[
            "registro_id"
        ] is not None:

            try:

                registro = (
                    RutaMonitoreada.objects.get(
                        pk=fila[
                            "registro_id"
                        ]
                    )
                )

            except (
                RutaMonitoreada
                .DoesNotExist
            ):

                continue


            # -----------------------------------------------------------------
            # MARCADA
            # -----------------------------------------------------------------

            if seleccionada:

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

                    registro.save()

                    actualizadas += 1


                # -------------------------------------------------------------
                # IMPORTANTE
                # -------------------------------------------------------------
                #
                # Permitimos mantenerla activa si el usuario así lo decide,
                # pero contamos la situación para advertirla.
                #
                # La medición podrá quedar PARCIAL mientras la ruta no exista.
                # -------------------------------------------------------------

                if (
                    not fila["existe"]
                    or
                    not fila[
                        "es_directorio"
                    ]
                    or
                    not fila["lectura"]
                ):

                    activas_sin_ruta += 1


            # -----------------------------------------------------------------
            # DESMARCADA
            # -----------------------------------------------------------------

            else:

                if registro.activa:

                    registro.activa = False

                    registro.save()

                    desactivadas += 1


            continue


        # =====================================================================
        # DIRECTORIO NUEVO DESCUBIERTO
        # =====================================================================

        if not seleccionada:

            continue


        # Una ruta nueva solamente puede registrarse
        # si actualmente existe como directorio.

        if (
            not fila["existe"]
            or
            not fila[
                "es_directorio"
            ]
        ):

            continue


        nombre = (
            _nombre_unico(
                fila["nombre"]
            )
        )


        RutaMonitoreada.objects.create(

            nombre=nombre,

            ruta=fila[
                "ruta_relativa"
            ],

            relativa_a_base_dir=True,

            categoria=categoria,

            recursiva=True,

            seguir_enlaces_simbolicos=False,

            patrones_incluir=[],

            patrones_excluir=[],

            activa=True,

            visible_dashboard=True,

            # -------------------------------------------------------------
            # SEGURIDAD
            # -------------------------------------------------------------
            #
            # Monitorizar jamás concede automáticamente
            # permiso para mantenimiento.
            # -------------------------------------------------------------

            permite_mantenimiento=False,

            observaciones=(
                "Ruta configurada "
                "mediante ESP005."
            ),
        )


        creadas += 1


    return {
        "creadas": creadas,

        "activadas": activadas,

        "desactivadas": (
            desactivadas
        ),

        "actualizadas": (
            actualizadas
        ),

        "activas_sin_ruta": (
            activas_sin_ruta
        ),

        "error": "",
    }