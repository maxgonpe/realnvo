from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .filetype_selector import (
    guardar_selector_tipos,
    obtener_selector_tipos,
)
from .models import EjecucionMedicion
from .route_selector import (
    guardar_seleccion_rutas,
    obtener_selector_rutas,
)
from .scanner import ejecutar_medicion_completa
from .services import obtener_dashboard_espaciometro
from .structure import analizar_estructura_proyecto


# =============================================================================
# DASHBOARD
# =============================================================================


@login_required
def dashboard(request):

    datos = (
        obtener_dashboard_espaciometro()
    )

    datos["ultima_medicion"] = (
        EjecucionMedicion.objects
        .order_by("-iniciada_en")
        .first()
    )

    datos["ultimas_mediciones"] = (
        EjecucionMedicion.objects
        .order_by("-iniciada_en")[:5]
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


    if resultado["error"]:

        messages.error(
            request,
            resultado["error"],
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
    """
    Configuración de tipos y extensiones
    de interés por ruta.
    """

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
    """
    Guarda la configuración ESP006.
    """

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