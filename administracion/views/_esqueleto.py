"""Helpers compartidos para pantallas-esqueleto de la Gantt."""
from django.shortcuts import render


def render_esqueleto(request, codigo: str, titulo: str, template_name: str, **extra):
    """Renderiza una ficha de esqueleto con contexto uniforme."""
    context = {
        "codigo_gantt": codigo,
        "titulo_esqueleto": titulo,
        "mensaje_esqueleto": (
            f"Esqueleto {codigo}: {titulo}. "
            "Ruta y plantilla listas; falta el corte vertical "
            "(servicio → selector → form → lógica)."
        ),
        **extra,
    }
    return render(request, template_name, context)
