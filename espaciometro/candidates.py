from __future__ import annotations

import os

from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone

from .classifier import (
    CATEGORIAS,
    clasificar_archivo,
    extension_normalizada,
)
from .inventory import (
    ORDENES,
    UNIDADES,
    buscar_inventario,
)
from .models import (
    CandidatoMantenimiento,
    LoteCandidatosMantenimiento,
    RutaMonitoreada,
    bytes_legibles,
)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================


SALT_CANDIDATO = (
    "espaciometro.esp012.candidato"
)

SALT_FILTROS = (
    "espaciometro.esp012.filtros"
)


MAX_EDAD_TOKEN_SEGUNDOS = (
    4 * 60 * 60
)


MAX_CANDIDATOS_POR_LOTE = 500


ANTIGUEDADES = (
    (
        "",
        "Cualquier antigüedad",
    ),
    (
        "90",
        "Más de 90 días",
    ),
    (
        "180",
        "Más de 180 días",
    ),
    (
        "365",
        "Más de 1 año",
    ),
    (
        "730",
        "Más de 2 años",
    ),
    (
        "1095",
        "Más de 3 años",
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


    minimo = str(
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


    maximo = str(
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


    antiguedad = str(
        params.get(
            "antiguedad",
            "",
        )
        or ""
    ).strip()


    antiguedades_validas = {
        codigo
        for codigo, nombre
        in ANTIGUEDADES
    }


    if antiguedad not in antiguedades_validas:

        antiguedad = ""


    orden = str(
        params.get(
            "orden",
            "tamano_desc",
        )
        or "tamano_desc"
    )


    ordenes_validos = {
        codigo
        for codigo, nombre
        in ORDENES
    }


    if orden not in ordenes_validos:

        orden = "tamano_desc"


    return {
        "ruta": ruta,
        "tipo": tipo,
        "extension": extension,
        "texto": texto,

        "minimo": minimo,
        "minimo_unidad": minimo_unidad,

        "maximo": maximo,
        "maximo_unidad": maximo_unidad,

        "antiguedad": antiguedad,

        "orden": orden,
    }


def _params_inventario(
    filtros: dict,
) -> dict:
    """
    Traduce ESP012 a los filtros ya probados
    de ESP010.
    """

    params = {
        "ruta": filtros[
            "ruta"
        ],

        "tipo": filtros[
            "tipo"
        ],

        "extension": filtros[
            "extension"
        ],

        "texto": filtros[
            "texto"
        ],

        "minimo": filtros[
            "minimo"
        ],

        "minimo_unidad": filtros[
            "minimo_unidad"
        ],

        "maximo": filtros[
            "maximo"
        ],

        "maximo_unidad": filtros[
            "maximo_unidad"
        ],

        "orden": filtros[
            "orden"
        ],
    }


    if filtros[
        "antiguedad"
    ]:

        dias = int(
            filtros[
                "antiguedad"
            ]
        )


        fecha_hasta = (
            timezone.localdate()
            - timedelta(
                days=dias
            )
        )


        params[
            "fecha_hasta"
        ] = (
            fecha_hasta.isoformat()
        )


    return params


# =============================================================================
# CONFIGURACIÓN DE PANTALLA
# =============================================================================


def obtener_configuracion_candidatos(
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

        "antiguedades": (
            ANTIGUEDADES
        ),

        "filtros": (
            _filtros_desde_params(
                params
            )
        ),
    }


# =============================================================================
# BÚSQUEDA ESP012
# =============================================================================


def buscar_candidatos(
    params,
) -> dict:

    filtros = (
        _filtros_desde_params(
            params
        )
    )


    params_inventario = (
        _params_inventario(
            filtros
        )
    )


    resultado = (
        buscar_inventario(
            params_inventario
        )
    )


    resultado[
        "filtros_esp012"
    ] = filtros


    resultado[
        "filtros_token"
    ] = signing.dumps(
        filtros,
        salt=SALT_FILTROS,
        compress=True,
    )


    # =========================================================================
    # TOKEN SEGURO POR ARCHIVO
    # =========================================================================

    if not resultado.get(
        "error"
    ):

        for archivo in resultado[
            "archivos"
        ]:

            archivo[
                "candidato_token"
            ] = signing.dumps(
                {
                    "ruta_id": (
                        archivo[
                            "ruta_id"
                        ]
                    ),

                    "ruta_relativa": (
                        archivo[
                            "ruta_relativa"
                        ]
                    ),
                },
                salt=SALT_CANDIDATO,
                compress=True,
            )


    return resultado


# =============================================================================
# RESOLVER Y REVALIDAR ARCHIVO
# =============================================================================


def _resolver_archivo_candidato(
    ruta: RutaMonitoreada,
    ruta_relativa: str,
) -> tuple[Path, os.stat_result]:

    relativa = Path(
        str(
            ruta_relativa
            or ""
        )
    )


    if (
        not str(
            relativa
        )
        or relativa.is_absolute()
    ):

        raise ValueError(
            "Ruta relativa inválida."
        )


    raiz = (
        _resolver_raiz(
            ruta
        )
    )


    if (
        not raiz.exists()
        or not raiz.is_dir()
    ):

        raise ValueError(
            "La raíz monitorizada "
            "no está disponible."
        )


    candidato_sin_resolver = (
        raiz
        / relativa
    )


    # El inventario nunca selecciona symlinks,
    # pero volvemos a comprobarlo.

    if candidato_sin_resolver.is_symlink():

        raise ValueError(
            "El archivo es un enlace simbólico."
        )


    try:

        candidato = (
            candidato_sin_resolver.resolve(
                strict=True
            )
        )

    except (
        FileNotFoundError,
        OSError,
    ) as exc:

        raise ValueError(
            "El archivo ya no existe."
        ) from exc


    try:

        candidato.relative_to(
            raiz
        )

    except ValueError as exc:

        raise ValueError(
            "El archivo está fuera "
            "de la ruta monitorizada."
        ) from exc


    if not candidato.is_file():

        raise ValueError(
            "La ubicación ya no corresponde "
            "a un archivo regular."
        )


    try:

        stat = os.stat(
            candidato,
            follow_symlinks=False,
        )

    except OSError as exc:

        raise ValueError(
            "No fue posible leer "
            "los metadatos del archivo."
        ) from exc


    return (
        candidato,
        stat,
    )


# =============================================================================
# CREAR LOTE
# =============================================================================


def crear_lote_candidatos(
    *,
    tokens: list[str],
    filtros_token: str,
    usuario: str = "",
    nombre: str = "",
) -> dict:

    resultado = {
        "lote": None,

        "creados": 0,

        "omitidos": 0,

        "errores": [],

        "error": "",
    }


    # =========================================================================
    # LÍMITE
    # =========================================================================

    tokens = list(
        dict.fromkeys(
            tokens
        )
    )


    if not tokens:

        resultado[
            "error"
        ] = (
            "Debe seleccionar al menos "
            "un archivo."
        )

        return resultado


    if len(
        tokens
    ) > MAX_CANDIDATOS_POR_LOTE:

        resultado[
            "error"
        ] = (
            "El lote supera el máximo "
            f"de {MAX_CANDIDATOS_POR_LOTE} "
            "archivos por operación."
        )

        return resultado


    # =========================================================================
    # FILTROS
    # =========================================================================

    try:

        filtros = signing.loads(
            filtros_token,
            salt=SALT_FILTROS,
            max_age=(
                MAX_EDAD_TOKEN_SEGUNDOS
            ),
        )

    except signing.BadSignature:

        resultado[
            "error"
        ] = (
            "La búsqueda expiró o "
            "su información no es válida. "
            "Ejecute nuevamente la búsqueda."
        )

        return resultado


    # =========================================================================
    # RESOLVER TOKENS
    # =========================================================================

    candidatos_validos = []

    vistos = set()


    for token in tokens:

        try:

            datos = signing.loads(
                token,
                salt=SALT_CANDIDATO,
                max_age=(
                    MAX_EDAD_TOKEN_SEGUNDOS
                ),
            )


            ruta_id = int(
                datos[
                    "ruta_id"
                ]
            )


            ruta_relativa = str(
                datos[
                    "ruta_relativa"
                ]
            )


        except (
            signing.BadSignature,
            KeyError,
            TypeError,
            ValueError,
        ):

            resultado[
                "omitidos"
            ] += 1

            resultado[
                "errores"
            ].append(
                "Se omitió una selección inválida."
            )

            continue


        clave = (
            ruta_id,
            ruta_relativa,
        )


        if clave in vistos:

            continue


        vistos.add(
            clave
        )


        try:

            ruta = (
                RutaMonitoreada.objects.get(
                    pk=ruta_id,
                    activa=True,
                )
            )

        except (
            RutaMonitoreada
            .DoesNotExist
        ):

            resultado[
                "omitidos"
            ] += 1

            resultado[
                "errores"
            ].append(
                (
                    f"{ruta_relativa}: "
                    "la ruta monitorizada "
                    "ya no está activa."
                )
            )

            continue


        try:

            (
                path,
                stat,
            ) = _resolver_archivo_candidato(
                ruta,
                ruta_relativa,
            )

        except ValueError as exc:

            resultado[
                "omitidos"
            ] += 1

            resultado[
                "errores"
            ].append(
                (
                    f"{ruta.nombre}/"
                    f"{ruta_relativa}: "
                    f"{exc}"
                )
            )

            continue


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


        modificado = (
            datetime.fromtimestamp(
                stat.st_mtime,
                tz=(
                    timezone
                    .get_current_timezone()
                ),
            )
        )


        candidatos_validos.append(
            {
                "ruta": ruta,

                "ruta_relativa": (
                    ruta_relativa
                ),

                "nombre": (
                    path.name
                ),

                "categoria": (
                    categoria
                ),

                "extension": (
                    extension
                ),

                "total_bytes": int(
                    stat.st_size
                ),

                "mtime_ns": int(
                    stat.st_mtime_ns
                ),

                "inode": max(
                    int(
                        getattr(
                            stat,
                            "st_ino",
                            0,
                        )
                    ),
                    0,
                ),

                "dispositivo": max(
                    int(
                        getattr(
                            stat,
                            "st_dev",
                            0,
                        )
                    ),
                    0,
                ),

                "modificado": (
                    modificado
                ),

                "tipo_interes": (
                    categoria
                    in (
                        ruta.tipos_interes
                        or []
                    )
                ),

                "extension_interes": (
                    extension
                    in (
                        ruta.extensiones_interes
                        or []
                    )
                ),
            }
        )


    if not candidatos_validos:

        resultado[
            "error"
        ] = (
            "Ninguno de los archivos "
            "seleccionados continúa siendo válido."
        )

        return resultado


    # =========================================================================
    # GUARDAR ATÓMICAMENTE
    # =========================================================================

    with transaction.atomic():

        lote = (
            LoteCandidatosMantenimiento.objects.create(

                nombre=(
                    str(
                        nombre
                        or ""
                    ).strip()[
                        :150
                    ]
                ),

                creado_por=(
                    str(
                        usuario
                        or ""
                    )[
                        :150
                    ]
                ),

                filtros=(
                    filtros
                    if isinstance(
                        filtros,
                        dict,
                    )
                    else {}
                ),
            )
        )


        objetos = []


        total_bytes = 0


        for datos in candidatos_validos:

            total_bytes += (
                datos[
                    "total_bytes"
                ]
            )


            objetos.append(
                CandidatoMantenimiento(

                    lote=lote,

                    ruta_monitoreada=(
                        datos[
                            "ruta"
                        ]
                    ),

                    ruta_relativa=(
                        datos[
                            "ruta_relativa"
                        ]
                    ),

                    nombre=(
                        datos[
                            "nombre"
                        ][
                            :255
                        ]
                    ),

                    categoria=(
                        datos[
                            "categoria"
                        ][
                            :40
                        ]
                    ),

                    extension=(
                        datos[
                            "extension"
                        ][
                            :40
                        ]
                    ),

                    total_bytes_snapshot=(
                        datos[
                            "total_bytes"
                        ]
                    ),

                    mtime_ns_snapshot=(
                        datos[
                            "mtime_ns"
                        ]
                    ),

                    inode_snapshot=(
                        datos[
                            "inode"
                        ]
                    ),

                    dispositivo_snapshot=(
                        datos[
                            "dispositivo"
                        ]
                    ),

                    modificado_snapshot=(
                        datos[
                            "modificado"
                        ]
                    ),

                    tipo_interes_snapshot=(
                        datos[
                            "tipo_interes"
                        ]
                    ),

                    extension_interes_snapshot=(
                        datos[
                            "extension_interes"
                        ]
                    ),
                )
            )


        CandidatoMantenimiento.objects.bulk_create(
            objetos
        )


        lote.total_archivos = len(
            objetos
        )


        lote.total_bytes = (
            total_bytes
        )


        lote.save(
            update_fields=[
                "total_archivos",
                "total_bytes",
            ]
        )


    resultado[
        "lote"
    ] = lote


    resultado[
        "creados"
    ] = len(
        candidatos_validos
    )


    return resultado


# =============================================================================
# VALIDACIÓN ACTUAL DE UN CANDIDATO
# =============================================================================


def _estado_actual_candidato(
    candidato: CandidatoMantenimiento,
) -> dict:

    try:

        (
            path,
            stat,
        ) = _resolver_archivo_candidato(

            candidato.ruta_monitoreada,

            candidato.ruta_relativa,
        )

    except ValueError as exc:

        texto = str(
            exc
        )


        if (
            "no existe"
            in texto.lower()
        ):

            codigo = "AUSENTE"

        else:

            codigo = "PROBLEMA"


        return {
            "codigo": codigo,

            "texto": (
                "Ausente"
                if codigo == "AUSENTE"
                else "Problema"
            ),

            "detalle": texto,

            "actual_bytes": None,

            "actual_legible": "-",
        }


    actual_bytes = int(
        stat.st_size
    )


    cambios = []


    if (
        actual_bytes
        != candidato
        .total_bytes_snapshot
    ):

        cambios.append(
            "tamaño"
        )


    if (
        int(
            stat.st_mtime_ns
        )
        != candidato
        .mtime_ns_snapshot
    ):

        cambios.append(
            "fecha de modificación"
        )


    inode_actual = max(
        int(
            getattr(
                stat,
                "st_ino",
                0,
            )
        ),
        0,
    )


    dispositivo_actual = max(
        int(
            getattr(
                stat,
                "st_dev",
                0,
            )
        ),
        0,
    )


    if (
        candidato.inode_snapshot
        and inode_actual
        != candidato.inode_snapshot
    ):

        cambios.append(
            "identidad física"
        )


    if (
        candidato.dispositivo_snapshot
        and dispositivo_actual
        != candidato.dispositivo_snapshot
    ):

        if (
            "identidad física"
            not in cambios
        ):

            cambios.append(
                "identidad física"
            )


    if cambios:

        return {
            "codigo": "CAMBIADO",

            "texto": "Cambió",

            "detalle": (
                "Cambió: "
                + ", ".join(
                    cambios
                )
                + "."
            ),

            "actual_bytes": (
                actual_bytes
            ),

            "actual_legible": (
                bytes_legibles(
                    actual_bytes
                )
            ),
        }


    return {
        "codigo": "VIGENTE",

        "texto": "Vigente",

        "detalle": (
            "Coincide con la fotografía "
            "registrada en ESP012."
        ),

        "actual_bytes": (
            actual_bytes
        ),

        "actual_legible": (
            bytes_legibles(
                actual_bytes
            )
        ),
    }


# =============================================================================
# DETALLE DEL LOTE
# =============================================================================


def obtener_detalle_lote(
    lote: LoteCandidatosMantenimiento,
) -> dict:

    candidatos = list(
        lote.candidatos
        .select_related(
            "ruta_monitoreada"
        )
        .order_by(
            "ruta_monitoreada__nombre",
            "ruta_relativa",
        )
    )


    filas = []


    vigentes = 0

    cambiados = 0

    ausentes = 0

    problemas = 0


    for candidato in candidatos:

        estado = (
            _estado_actual_candidato(
                candidato
            )
        )


        if estado[
            "codigo"
        ] == "VIGENTE":

            vigentes += 1


        elif estado[
            "codigo"
        ] == "CAMBIADO":

            cambiados += 1


        elif estado[
            "codigo"
        ] == "AUSENTE":

            ausentes += 1


        else:

            problemas += 1


        filas.append(
            {
                "objeto": candidato,

                "estado": estado,

                "mantenimiento_permitido": (
                    candidato
                    .ruta_monitoreada
                    .permite_mantenimiento
                ),
            }
        )


    return {
        "lote": lote,

        "filas": filas,

        "total": len(
            filas
        ),

        "vigentes": vigentes,

        "cambiados": cambiados,

        "ausentes": ausentes,

        "problemas": problemas,

        "total_legible": (
            bytes_legibles(
                lote.total_bytes
            )
        ),
    }


# =============================================================================
# LOTES RECIENTES
# =============================================================================


def obtener_lotes_recientes(
    limite: int = 10,
):

    return (
        LoteCandidatosMantenimiento.objects
        .all()
        .order_by(
            "-creado_en"
        )[
            :limite
        ]
    )