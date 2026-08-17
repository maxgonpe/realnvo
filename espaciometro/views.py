from django.contrib import messages
from django.http import FileResponse

from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)

from .release import (
    evaluar_liberacion_lote,
    ejecutar_liberacion_lote,
    obtener_detalle_liberacion,
)

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.views.decorators.http import require_POST

from .dashboard_ops import (
    construir_dashboard_operativo,
)
from .directory_detail import (
    analizar_detalle_directorio,
)
from .filetype_selector import (
    guardar_selector_tipos,
    obtener_selector_tipos,
)
from .history import (
    obtener_evolucion_ruta,
    obtener_panel_historico,
)
from .inventory import (
    buscar_inventario,
    obtener_configuracion_inventario,
)
from .lifecycle import (
    analizar_ciclo_vida,
    obtener_configuracion_ciclo_vida,
)
from .models import (
    EjecucionMedicion,
    LoteCandidatosMantenimiento,
    RutaMonitoreada,
    RespaldoMantenimiento,
    RegistroDescargaRespaldo,
    LiberacionMantenimiento,
    RespaldoBaseDatos,
)
from .route_selector import (
    guardar_seleccion_rutas,
    obtener_selector_rutas,
)

from .candidates import (
    buscar_candidatos,
    crear_lote_candidatos,
    obtener_configuracion_candidatos,
    obtener_detalle_lote,
    obtener_lotes_recientes,
)

from .backup import (
    obtener_detalle_respaldo,
    obtener_respaldos_recientes,
    preparar_respaldo_lote,
)

from .downloads import (
    confirmar_descarga as confirmar_descarga_servicio,
    preparar_entrega_descarga,
)

from .backup_retirement import (
    evaluar_retiro_respaldo,
    ejecutar_retiro_respaldo,
)

from .audit import (
    construir_auditoria_general,
    construir_auditoria_lote,
)


from .database_monitor import (
    inspeccionar_base_datos,
)

from .database_backup import (
    ErrorRespaldoBaseDatos,
    crear_respaldo_base_datos,
    preparar_descarga_respaldo_bd,
)


from .scanner import ejecutar_medicion_completa
from .services import obtener_dashboard_espaciometro
from .structure import analizar_estructura_proyecto


# =============================================================================
# DASHBOARD — ESP007
# =============================================================================


@login_required
def dashboard(request):

    datos = (
        obtener_dashboard_espaciometro()
    )


    ultima_medicion = (
        EjecucionMedicion.objects
        .order_by("-iniciada_en")
        .first()
    )


    datos[
        "ultima_medicion"
    ] = ultima_medicion


    datos[
        "ultimas_mediciones"
    ] = (
        EjecucionMedicion.objects
        .order_by("-iniciada_en")[:5]
    )


    datos[
        "operativo"
    ] = (
        construir_dashboard_operativo(
            datos,
            ultima_medicion=(
                ultima_medicion
            ),
        )
    )


    return render(
        request,
        "espaciometro/dashboard.html",
        datos,
    )


# =============================================================================
# ESP002 / ESP003
# =============================================================================


@login_required
def estructura(request):

    datos = (
        analizar_estructura_proyecto()
    )


    return render(
        request,
        "espaciometro/estructura.html",
        {
            "estructura": datos,
        },
    )


# =============================================================================
# ESP004
# =============================================================================


@login_required
@require_POST
def ejecutar_medicion(request):

    ejecucion = (
        ejecutar_medicion_completa()
    )


    if (
        ejecucion.estado
        == EjecucionMedicion
        .Estado
        .COMPLETADA
    ):

        messages.success(
            request,
            (
                f"Medición #{ejecucion.pk} "
                "completada correctamente."
            ),
        )


    elif (
        ejecucion.estado
        == EjecucionMedicion
        .Estado
        .PARCIAL
    ):

        messages.warning(
            request,
            (
                f"Medición #{ejecucion.pk} "
                "terminó parcialmente."
            ),
        )


    else:

        messages.error(
            request,
            (
                f"Medición #{ejecucion.pk} "
                "terminó con errores."
            ),
        )


    return redirect(
        "espaciometro:dashboard"
    )


# =============================================================================
# ESP005
# =============================================================================


@login_required
def configurar_rutas(request):

    datos = (
        obtener_selector_rutas()
    )


    return render(
        request,
        "espaciometro/rutas.html",
        {
            "selector": datos,
        },
    )


@login_required
@require_POST
def guardar_rutas(request):

    resultado = (
        guardar_seleccion_rutas(
            request.POST
        )
    )


    if resultado[
        "error"
    ]:

        messages.error(
            request,
            resultado[
                "error"
            ],
        )


    else:

        texto = (
            "Configuración guardada. "
            f"Creadas: {resultado['creadas']}. "
            f"Activadas: {resultado['activadas']}. "
            f"Desactivadas: {resultado['desactivadas']}."
        )


        if resultado.get(
            "activas_sin_ruta"
        ):

            texto += (
                " Advertencia: "
                f"{resultado['activas_sin_ruta']} "
                "ruta(s) problemática(s) "
                "permanecen activas."
            )


        messages.success(
            request,
            texto,
        )


    return redirect(
        "espaciometro:configurar_rutas"
    )


# =============================================================================
# ESP006
# =============================================================================


@login_required
def configurar_tipos(request):

    datos = (
        obtener_selector_tipos()
    )


    return render(
        request,
        "espaciometro/tipos.html",
        {
            "selector": datos,
        },
    )


@login_required
@require_POST
def guardar_tipos(request):

    resultado = (
        guardar_selector_tipos(
            request.POST
        )
    )


    messages.success(
        request,
        (
            "Preferencias de archivos guardadas. "
            f"Rutas actualizadas: "
            f"{resultado['actualizadas']}. "
            f"Sin cambios: "
            f"{resultado['sin_cambios']}."
        ),
    )


    return redirect(
        "espaciometro:configurar_tipos"
    )


# =============================================================================
# ESP008
# =============================================================================


@login_required
def detalle_ruta(
    request,
    ruta_id,
):

    ruta = get_object_or_404(
        RutaMonitoreada,
        pk=ruta_id,
    )


    subruta = (
        request.GET.get(
            "sub",
            "",
        )
    )


    datos = (
        analizar_detalle_directorio(
            ruta,
            subruta=subruta,
        )
    )


    return render(
        request,
        "espaciometro/detalle_ruta.html",
        {
            "detalle": datos,
            "ruta_monitoreada": ruta,
        },
    )


# =============================================================================
# ESP009
# =============================================================================


@login_required
def historico(request):

    datos = (
        obtener_panel_historico()
    )


    return render(
        request,
        "espaciometro/historico.html",
        {
            "historico": datos,
        },
    )


@login_required
def evolucion_ruta(
    request,
    ruta_id,
):

    ruta = get_object_or_404(
        RutaMonitoreada,
        pk=ruta_id,
    )


    datos = (
        obtener_evolucion_ruta(
            ruta
        )
    )


    return render(
        request,
        "espaciometro/evolucion_ruta.html",
        {
            "evolucion": datos,
            "ruta_monitoreada": ruta,
        },
    )


# =============================================================================
# ESP010
# =============================================================================


@login_required
def inventario(request):

    configuracion = (
        obtener_configuracion_inventario(
            request.GET
        )
    )


    resultado = None


    if request.GET.get(
        "buscar"
    ):

        resultado = (
            buscar_inventario(
                request.GET
            )
        )


    return render(
        request,
        "espaciometro/inventario.html",
        {
            "inventario": configuracion,
            "resultado": resultado,
        },
    )


# =============================================================================
# ESP011 — CICLO DE VIDA
# =============================================================================


@login_required
def ciclo_vida(request):
    """
    La pantalla no escanea automáticamente.

    El análisis solamente se ejecuta cuando:
        ?analizar=1
    """

    configuracion = (
        obtener_configuracion_ciclo_vida(
            request.GET
        )
    )


    resultado = None


    if request.GET.get(
        "analizar"
    ):

        resultado = (
            analizar_ciclo_vida(
                request.GET
            )
        )


    return render(
        request,
        "espaciometro/ciclo_vida.html",
        {
            "ciclo": configuracion,
            "resultado": resultado,
        },
    )

# =============================================================================
# ESP012 — CANDIDATOS A MANTENIMIENTO
# =============================================================================


@login_required
def candidatos(request):
    """
    Abrir la pantalla no ejecuta búsqueda.

    Solo se analiza el filesystem cuando:
        ?buscar=1
    """

    configuracion = (
        obtener_configuracion_candidatos(
            request.GET
        )
    )


    resultado = None


    if request.GET.get(
        "buscar"
    ):

        resultado = (
            buscar_candidatos(
                request.GET
            )
        )


    lotes = (
        obtener_lotes_recientes()
    )


    return render(
        request,
        "espaciometro/candidatos.html",
        {
            "selector": configuracion,
            "resultado": resultado,
            "lotes": lotes,
        },
    )



@login_required
@require_POST
def crear_lote_candidatos_view(
    request,
):

    usuario = (
        request.user.get_username()
        or str(
            request.user
        )
    )


    resultado = (
        crear_lote_candidatos(

            tokens=(
                request.POST.getlist(
                    "seleccionados"
                )
            ),

            filtros_token=(
                request.POST.get(
                    "filtros_token",
                    "",
                )
            ),

            usuario=usuario,

            nombre=(
                request.POST.get(
                    "nombre_lote",
                    "",
                )
            ),
        )
    )


    if resultado[
        "error"
    ]:

        messages.error(
            request,
            resultado[
                "error"
            ],
        )


        return redirect(
            "espaciometro:candidatos"
        )


    texto = (
        f"Lote #{resultado['lote'].pk} "
        f"creado con "
        f"{resultado['creados']} "
        "archivo(s)."
    )


    if resultado[
        "omitidos"
    ]:

        texto += (
            f" Se omitieron "
            f"{resultado['omitidos']} "
            "selección(es) que ya no "
            "eran válidas."
        )


    messages.success(
        request,
        texto,
    )


    return redirect(
        "espaciometro:detalle_lote_candidatos",
        lote_id=(
            resultado[
                "lote"
            ].pk
        ),
    )



@login_required
def detalle_lote_candidatos(
    request,
    lote_id,
):

    lote = get_object_or_404(
        LoteCandidatosMantenimiento,
        pk=lote_id,
    )


    detalle = (
        obtener_detalle_lote(
            lote
        )
    )

    detalle[
    "respaldos"
    ] = (
        lote.respaldos
        .all()
        .order_by(
            "-creado_en"
        )
    )

    return render(
        request,
        "espaciometro/lote_candidatos.html",
        {
            "detalle": detalle,
        },
    )

# =============================================================================
# ESP013 — RESPALDOS
# =============================================================================


@login_required
def respaldos(request):

    datos = (
        obtener_respaldos_recientes()
    )


    return render(
        request,
        "espaciometro/respaldos.html",
        {
            "respaldos": datos,
        },
    )



@login_required
@require_POST
def preparar_respaldo(
    request,
    lote_id,
):

    lote = get_object_or_404(
        LoteCandidatosMantenimiento,
        pk=lote_id,
    )


    usuario = (
        request.user.get_username()
        or str(
            request.user
        )
    )


    resultado = (
        preparar_respaldo_lote(
            lote=lote,
            usuario=usuario,
        )
    )


    respaldo = (
        resultado[
            "respaldo"
        ]
    )


    if resultado[
        "error"
    ]:

        messages.error(
            request,
            resultado[
                "error"
            ],
        )


        if respaldo:

            return redirect(
                "espaciometro:detalle_respaldo",
                respaldo_id=(
                    respaldo.pk
                ),
            )


        return redirect(
            "espaciometro:detalle_lote_candidatos",
            lote_id=lote.pk,
        )


    if (
        resultado[
            "estado"
        ]
        == RespaldoMantenimiento
        .Estado
        .LISTO
    ):

        messages.success(
            request,
            (
                "Respaldo preparado y "
                "verificado correctamente. "
                f"Archivos incluidos: "
                f"{resultado['incluidos']}."
            ),
        )


    else:

        messages.warning(
            request,
            (
                "Se preparó un respaldo parcial. "
                f"Incluidos: "
                f"{resultado['incluidos']}. "
                f"Omitidos: "
                f"{resultado['omitidos']}."
            ),
        )


    return redirect(
        "espaciometro:detalle_respaldo",
        respaldo_id=(
            respaldo.pk
        ),
    )



@login_required
def detalle_respaldo(
    request,
    respaldo_id,
):

    respaldo = get_object_or_404(
        RespaldoMantenimiento,
        pk=respaldo_id,
    )


    detalle = (
        obtener_detalle_respaldo(
            respaldo
        )
    )

    detalle[
    "descargas"
    ] = (
        respaldo.descargas
        .all()
        .order_by(
            "-iniciada_en"
        )
    )

    return render(
        request,
        "espaciometro/respaldo_detalle.html",
        {
            "detalle": detalle,
        },
    )

# =============================================================================
# ESP014 — DESCARGA SEGURA
# =============================================================================


@login_required
@require_POST
def descargar_respaldo(
    request,
    respaldo_id,
):

    respaldo = get_object_or_404(
        RespaldoMantenimiento,
        pk=respaldo_id,
    )


    usuario = (
        request.user.get_username()
        or str(
            request.user
        )
    )


    ip_cliente = (
        request.META.get(
            "REMOTE_ADDR",
            "",
        )
    )


    user_agent = (
        request.META.get(
            "HTTP_USER_AGENT",
            "",
        )
    )


    resultado = (
        preparar_entrega_descarga(

            respaldo=respaldo,

            usuario=usuario,

            ip_cliente=ip_cliente,

            user_agent=user_agent,
        )
    )


    if resultado[
        "error"
    ]:

        messages.error(
            request,
            resultado[
                "error"
            ],
        )


        return redirect(
            "espaciometro:detalle_respaldo",
            respaldo_id=respaldo.pk,
        )


    respuesta = FileResponse(

        resultado[
            "archivo"
        ],

        as_attachment=True,

        filename=(
            resultado[
                "nombre_archivo"
            ]
        ),

        content_type=(
            "application/zip"
        ),
    )


    respuesta[
        "Cache-Control"
    ] = (
        "private, no-store"
    )


    respuesta[
        "X-Content-Type-Options"
    ] = "nosniff"


    respuesta[
        "X-Espaciometro-Download-Id"
    ] = str(
        resultado[
            "registro"
        ].pk
    )


    return respuesta



@login_required
@require_POST
def confirmar_descarga_view(
    request,
    descarga_id,
):

    registro = get_object_or_404(
        RegistroDescargaRespaldo,
        pk=descarga_id,
    )


    usuario_actual = (
        request.user.get_username()
        or str(
            request.user
        )
    )


    if (
        registro.usuario
        and registro.usuario
        != usuario_actual
        and not request.user.is_superuser
    ):

        messages.error(
            request,
            (
                "Esta entrega fue iniciada "
                "por otro usuario."
            ),
        )


        return redirect(
            "espaciometro:detalle_respaldo",
            respaldo_id=(
                registro.respaldo_id
            ),
        )


    resultado = (
        confirmar_descarga_servicio(

            registro=registro,

            sha256_cliente=(
                request.POST.get(
                    "sha256_cliente",
                    "",
                )
            ),
        )
    )


    if resultado[
        "error"
    ]:

        messages.error(
            request,
            resultado[
                "error"
            ],
        )


    else:

        messages.success(
            request,
            resultado[
                "mensaje"
            ],
        )


    return redirect(
        "espaciometro:detalle_respaldo",
        respaldo_id=(
            registro.respaldo_id
        ),
    )

# =============================================================================
# ESP015 — LIBERACIÓN SEGURA
# =============================================================================


@login_required
def evaluar_liberacion_view(
    request,
    lote_id,
):

    lote = get_object_or_404(
        LoteCandidatosMantenimiento,
        pk=lote_id,
    )


    evaluacion = (
        evaluar_liberacion_lote(
            lote
        )
    )


    return render(
        request,
        "espaciometro/liberacion_evaluacion.html",
        {
            "evaluacion": evaluacion,
        },
    )



@login_required
@permission_required(
    "espaciometro.puede_liberar_archivos",
    raise_exception=True,
)
@require_POST
def ejecutar_liberacion_view(
    request,
    lote_id,
):

    lote = get_object_or_404(
        LoteCandidatosMantenimiento,
        pk=lote_id,
    )


    usuario = (
        request.user.get_username()
        or str(
            request.user
        )
    )


    resultado = (
        ejecutar_liberacion_lote(

            lote=lote,

            usuario=usuario,

            confirmacion=(
                request.POST.get(
                    "confirmacion",
                    "",
                )
            ),
        )
    )


    liberacion = (
        resultado[
            "liberacion"
        ]
    )


    if resultado[
        "error"
    ]:

        messages.error(
            request,
            resultado[
                "error"
            ],
        )


        if liberacion:

            return redirect(
                "espaciometro:detalle_liberacion",
                liberacion_id=(
                    liberacion.pk
                ),
            )


        return redirect(
            "espaciometro:evaluar_liberacion",
            lote_id=lote.pk,
        )


    messages.success(
        request,
        (
            "Liberación completada. "
            f"Archivos eliminados: "
            f"{resultado['liberados']}."
        ),
    )


    return redirect(
        "espaciometro:detalle_liberacion",
        liberacion_id=(
            liberacion.pk
        ),
    )



@login_required
def detalle_liberacion_view(
    request,
    liberacion_id,
):

    liberacion = get_object_or_404(
        LiberacionMantenimiento,
        pk=liberacion_id,
    )


    detalle = (
        obtener_detalle_liberacion(
            liberacion
        )
    )


    return render(
        request,
        "espaciometro/liberacion_detalle.html",
        {
            "detalle": detalle,
        },
    )


# =============================================================================
# ESP015 — RETIRO DEL ZIP PRIVADO
# =============================================================================


@login_required
def evaluar_retiro_respaldo_view(
    request,
    respaldo_id,
):

    respaldo = get_object_or_404(
        RespaldoMantenimiento,
        pk=respaldo_id,
    )


    evaluacion = (
        evaluar_retiro_respaldo(
            respaldo
        )
    )


    return render(
        request,
        "espaciometro/retiro_respaldo_evaluacion.html",
        {
            "evaluacion": evaluacion,
        },
    )



@login_required
@permission_required(
    "espaciometro.puede_liberar_archivos",
    raise_exception=True,
)
@require_POST
def ejecutar_retiro_respaldo_view(
    request,
    respaldo_id,
):

    respaldo = get_object_or_404(
        RespaldoMantenimiento,
        pk=respaldo_id,
    )


    usuario = (
        request.user.get_username()
        or str(
            request.user
        )
    )


    resultado = (
        ejecutar_retiro_respaldo(

            respaldo=respaldo,

            usuario=usuario,

            confirmacion=(
                request.POST.get(
                    "confirmacion",
                    "",
                )
            ),
        )
    )


    if resultado[
        "error"
    ]:

        messages.error(
            request,
            resultado[
                "error"
            ],
        )


    else:

        messages.success(
            request,
            (
                "La copia temporal del respaldo "
                "fue retirada del servidor "
                "correctamente."
            ),
        )


    return redirect(
        "espaciometro:detalle_respaldo",
        respaldo_id=respaldo.pk,
    )

# =============================================================================
# ESP016 — AUDITORÍA
# =============================================================================


@login_required
def auditoria_view(
    request,
):

    limite = (
        request.GET.get(
            "limite",
            "100",
        )
    )


    auditoria = (
        construir_auditoria_general(
            limite=limite
        )
    )


    return render(
        request,
        "espaciometro/auditoria.html",
        {
            "auditoria": auditoria,
        },
    )



@login_required
def auditoria_lote_view(
    request,
    lote_id,
):

    lote = get_object_or_404(
        LoteCandidatosMantenimiento,
        pk=lote_id,
    )


    auditoria = (
        construir_auditoria_lote(
            lote
        )
    )


    return render(
        request,
        "espaciometro/auditoria_lote.html",
        {
            "auditoria": auditoria,
        },
    )


# =============================================================================
# ESP020 — INVENTARIO DE BASE DE DATOS
# =============================================================================


@login_required
def base_datos_view(
    request,
):

    contar = (
        request.GET.get(
            "contar"
        )
        == "1"
    )


    inventario = (
        inspeccionar_base_datos(
            contar_registros=contar
        )
    )


    respaldos_bd = (
        RespaldoBaseDatos
        .objects
        .all()
        .order_by(
            "-creado_en",
            "-id",
        )[
            :20
        ]
    )


    ultimo_respaldo = (
        RespaldoBaseDatos
        .objects
        .filter(
            estado=(
                RespaldoBaseDatos
                .Estado
                .VERIFICADO
            )
        )
        .order_by(
            "-verificado_en",
            "-id",
        )
        .first()
    )


    return render(
        request,
        "espaciometro/base_datos.html",
        {
            "inventario": inventario,
            "respaldos_bd": respaldos_bd,
            "ultimo_respaldo": ultimo_respaldo,
        },
    )

@login_required
@permission_required(
    "espaciometro.puede_gestionar_respaldos_bd",
    raise_exception=True,
)
@require_POST
def crear_respaldo_base_datos_view(
    request,
):

    usuario = (
        request.user.get_username()
        if request.user.is_authenticated
        else ""
    )


    try:

        respaldo = (
            crear_respaldo_base_datos(
                usuario=usuario
            )
        )


        messages.success(
            request,
            (
                "Respaldo de base de datos "
                f"#{respaldo.pk} creado y "
                "verificado correctamente."
            ),
        )


    except ErrorRespaldoBaseDatos as exc:

        messages.error(
            request,
            (
                "No fue posible crear "
                "el respaldo de base "
                f"de datos: {exc}"
            ),
        )


    return redirect(
        "espaciometro:base_datos"
    )



@login_required
@permission_required(
    "espaciometro.puede_gestionar_respaldos_bd",
    raise_exception=True,
)
def descargar_respaldo_base_datos_view(
    request,
    respaldo_id,
):

    respaldo = get_object_or_404(
        RespaldoBaseDatos,
        pk=respaldo_id,
    )


    try:

        entrega = (
            preparar_descarga_respaldo_bd(
                respaldo
            )
        )


    except ErrorRespaldoBaseDatos as exc:

        messages.error(
            request,
            str(
                exc
            ),
        )


        return redirect(
            "espaciometro:base_datos"
        )


    return FileResponse(
        entrega[
            "archivo"
        ],
        as_attachment=True,
        filename=(
            entrega[
                "nombre"
            ]
        ),
        content_type=(
            "application/octet-stream"
        ),
    )