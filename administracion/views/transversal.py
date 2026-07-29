"""
A004–A007 + maestros de rendición R003–R004.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms.maestros_rendicion import ResponsableRendicionForm
from ..models import ResponsableRendicion
from ..selectors.rendiciones import listar_responsables, resumen_responsable
from ..services.rendiciones import (
    activar_responsable,
    actualizar_responsable,
    crear_responsable,
    desactivar_responsable,
)
from ._esqueleto import render_esqueleto


@login_required
def panel_administracion(request):
    """A007 — Navegación / panel del módulo."""
    return render_esqueleto(
        request,
        "A007",
        "Panel Administración",
        "administracion/transversal/panel.html",
    )


@login_required
def responsable_lista(request):
    """R003 — Lista de responsables."""
    q = request.GET.get("q", "")
    estado = request.GET.get("estado", "todos")
    solo_activos = None
    if estado == "activos":
        solo_activos = True
    elif estado == "inactivos":
        solo_activos = False

    responsables = listar_responsables(q=q, solo_activos=solo_activos)
    return render(
        request,
        "administracion/rendiciones/responsable_lista.html",
        {
            "responsables": responsables,
            "q": q,
            "estado": estado,
            "codigo_gantt": "R003",
            "titulo_esqueleto": "Responsables de rendición",
        },
    )


@login_required
def responsable_detalle(request, pk):
    """R003 — Detalle de responsable."""
    responsable = get_object_or_404(
        ResponsableRendicion.objects.select_related("user"), pk=pk
    )
    return render(
        request,
        "administracion/rendiciones/responsable_detalle.html",
        {
            "responsable": responsable,
            "resumen": resumen_responsable(responsable),
            "codigo_gantt": "R003",
        },
    )


@login_required
def responsable_crear(request):
    """R003 — Alta de responsable."""
    form = ResponsableRendicionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            responsable = crear_responsable(
                datos=form.cleaned_data, usuario=request.user
            )
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errs in exc.message_dict.items():
                    for err in errs:
                        form.add_error(field if field in form.fields else None, err)
            else:
                form.add_error(None, exc)
        else:
            messages.success(request, f"Responsable «{responsable.nombre}» creado.")
            return redirect("adm_responsable_detalle", pk=responsable.pk)

    return render(
        request,
        "administracion/rendiciones/responsable_form.html",
        {
            "form": form,
            "modo": "crear",
            "codigo_gantt": "R003",
            "titulo_esqueleto": "Nuevo responsable",
        },
    )


@login_required
def responsable_editar(request, pk):
    """R003 — Edición de responsable."""
    responsable = get_object_or_404(ResponsableRendicion, pk=pk)
    form = ResponsableRendicionForm(request.POST or None, instance=responsable)
    if request.method == "POST" and form.is_valid():
        try:
            responsable = actualizar_responsable(
                responsable=responsable,
                datos=form.cleaned_data,
                usuario=request.user,
            )
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errs in exc.message_dict.items():
                    for err in errs:
                        form.add_error(field if field in form.fields else None, err)
            else:
                form.add_error(None, exc)
        else:
            messages.success(request, f"Responsable «{responsable.nombre}» actualizado.")
            return redirect("adm_responsable_detalle", pk=responsable.pk)

    return render(
        request,
        "administracion/rendiciones/responsable_form.html",
        {
            "form": form,
            "responsable": responsable,
            "modo": "editar",
            "codigo_gantt": "R003",
            "titulo_esqueleto": f"Editar — {responsable.nombre}",
        },
    )


@login_required
@require_POST
def responsable_activar(request, pk):
    """R003 — Reactivar responsable."""
    responsable = get_object_or_404(ResponsableRendicion, pk=pk)
    try:
        activar_responsable(responsable=responsable, usuario=request.user)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, f"Responsable «{responsable.nombre}» activado.")
    return redirect("adm_responsable_detalle", pk=pk)


@login_required
@require_POST
def responsable_desactivar(request, pk):
    """R003 — Desactivar responsable (no borra historial)."""
    responsable = get_object_or_404(ResponsableRendicion, pk=pk)
    desactivar_responsable(responsable=responsable, usuario=request.user)
    messages.success(request, f"Responsable «{responsable.nombre}» desactivado.")
    return redirect("adm_responsable_detalle", pk=pk)


@login_required
def categoria_lista(request):
    """R004 — Categorías y subcategorías."""
    return render_esqueleto(
        request,
        "R004",
        "Categorías de gasto",
        "administracion/rendiciones/categoria_lista.html",
    )
