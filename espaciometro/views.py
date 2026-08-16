from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import obtener_dashboard_espaciometro
from .structure import analizar_estructura_proyecto


@login_required
def dashboard(request):
    """
    Dashboard inicial del Espaciómetro.

    En esta primera etapa realiza una medición en vivo
    y no persiste históricos.
    """

    datos = obtener_dashboard_espaciometro()

    return render(
        request,
        "espaciometro/dashboard.html",
        datos,
    )

@login_required
def estructura(request):
    """
    ESP002 — Explorador estructural del proyecto anfitrión.
    """

    datos = analizar_estructura_proyecto()

    return render(
        request,
        "espaciometro/estructura.html",
        {
            "estructura": datos,
        },
    )