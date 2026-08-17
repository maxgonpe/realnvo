from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
    RutaMonitoreada,
)
from .route_selector import (
    guardar_seleccion_rutas,
    obtener_selector_rutas,
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