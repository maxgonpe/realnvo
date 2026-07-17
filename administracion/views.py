import os
import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from weasyprint import HTML

from .forms import (
    ConfirmarDetalleComprobanteForm,
    EditarDetalleRendicionForm,
    NuevaRendicionForm,
    SubirImagenComprobanteForm,
    crear_rendicion,
)
from .models import AprobacionRendicion, DetalleRendicion, Rendicion
from .ocr_comprobante import extraer_datos_comprobante


def _tmp_dir() -> Path:
    path = Path(settings.MEDIA_ROOT) / "administracion" / "tmp_ocr"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _contexto_progreso(rendicion: Rendicion) -> dict:
    detalles = list(
        rendicion.detalles.exclude(
            estado_revision=DetalleRendicion.EstadoRevision.RECHAZADO
        ).order_by("fecha", "id")
    )
    agregados = rendicion.detalles.exclude(
        estado_revision=DetalleRendicion.EstadoRevision.RECHAZADO
    ).aggregate(cantidad=Count("id"), suma=Sum("total"))
    return {
        "detalles": detalles,
        "cantidad_soportes": agregados["cantidad"] or 0,
        "suma_soportes": agregados["suma"] or Decimal("0.00"),
        "carga_abierta": rendicion.estado == Rendicion.Estado.BORRADOR,
    }


def _puede_editar_detalles(rendicion: Rendicion) -> bool:
    return rendicion.estado not in (
        Rendicion.Estado.APROBADA,
        Rendicion.Estado.LIQUIDADA,
        Rendicion.Estado.CERRADA,
        Rendicion.Estado.ANULADA,
    )


# ---------------------------------------------------------------------------
# Lista e inicio de rendición
# ---------------------------------------------------------------------------

@login_required
def rendicion_lista(request):
    qs = (
        Rendicion.objects.select_related("responsable")
        .annotate(
            n_detalles=Count("detalles"),
            suma_detalles=Sum("detalles__total"),
        )
        .order_by("-creado_en", "-id")
    )
    return render(
        request,
        "administracion/rendicion_lista.html",
        {"rendiciones": qs},
    )


@login_required
@require_http_methods(["GET", "POST"])
def rendicion_crear(request):
    """Momento claro de INICIAR una rendición (solo cabecera)."""
    if request.method == "POST":
        form = NuevaRendicionForm(request.POST)
        if form.is_valid():
            rendicion = crear_rendicion(request.user, form.cleaned_data)
            messages.success(
                request,
                f"Rendición {rendicion.numero} iniciada. Ahora agregue comprobantes.",
            )
            return redirect("adm_rendicion_escritorio", pk=rendicion.pk)
    else:
        form = NuevaRendicionForm()
    return render(
        request,
        "administracion/rendicion_crear.html",
        {"form": form},
    )


# ---------------------------------------------------------------------------
# Escritorio: ver/editar detalles de una rendición
# ---------------------------------------------------------------------------

@login_required
def rendicion_escritorio(request, pk):
    """
    Pantalla principal de trabajo:
    cabecera + tabla de detalles (BD) + agregar/editar/eliminar comprobantes.
    """
    rendicion = get_object_or_404(
        Rendicion.objects.select_related("responsable"), pk=pk
    )
    progreso = _contexto_progreso(rendicion)
    return render(
        request,
        "administracion/rendicion_escritorio.html",
        {
            "rendicion": rendicion,
            **progreso,
            "puede_editar": _puede_editar_detalles(rendicion),
            "diferencia_fondos": rendicion.total_fondos - rendicion.total_rendido,
            "form_imagen": SubirImagenComprobanteForm(),
        },
    )


# Alias: resumen apunta al escritorio
@login_required
def rendicion_resumen(request, pk):
    return redirect("adm_rendicion_escritorio", pk=pk)


@login_required
@require_http_methods(["GET", "POST"])
def detalle_editar(request, pk):
    detalle = get_object_or_404(
        DetalleRendicion.objects.select_related("rendicion"), pk=pk
    )
    rendicion = detalle.rendicion
    if not _puede_editar_detalles(rendicion):
        messages.error(request, "Esta rendición no permite editar comprobantes.")
        return redirect("adm_rendicion_escritorio", pk=rendicion.pk)

    if request.method == "POST":
        form = EditarDetalleRendicionForm(request.POST, request.FILES, instance=detalle)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.actualizado_por = request.user
            obj.full_clean()
            obj.save()
            messages.success(request, f"Comprobante #{detalle.pk} actualizado.")
            return redirect("adm_rendicion_escritorio", pk=rendicion.pk)
    else:
        form = EditarDetalleRendicionForm(instance=detalle)

    return render(
        request,
        "administracion/detalle_editar.html",
        {
            "form": form,
            "detalle": detalle,
            "rendicion": rendicion,
        },
    )


@login_required
@require_POST
def detalle_eliminar(request, pk):
    detalle = get_object_or_404(
        DetalleRendicion.objects.select_related("rendicion"), pk=pk
    )
    rendicion = detalle.rendicion
    if not _puede_editar_detalles(rendicion) or rendicion.estado != Rendicion.Estado.BORRADOR:
        messages.error(
            request,
            "Solo se pueden eliminar comprobantes mientras la carga esté abierta (borrador).",
        )
        return redirect("adm_rendicion_escritorio", pk=rendicion.pk)

    det_id = detalle.pk
    if detalle.comprobante:
        detalle.comprobante.delete(save=False)
    detalle.delete()
    messages.success(request, f"Comprobante #{det_id} eliminado.")
    return redirect("adm_rendicion_escritorio", pk=rendicion.pk)


# ---------------------------------------------------------------------------
# Agregar comprobante desde imagen (OCR) — siempre dentro de una rendición
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["GET", "POST"])
def rendicion_agregar_comprobante(request, pk):
    """Sube imagen → OCR → confirma → guarda DetalleRendicion en esta rendición."""
    rendicion = get_object_or_404(Rendicion, pk=pk)

    if rendicion.estado != Rendicion.Estado.BORRADOR:
        messages.warning(
            request,
            "La carga está cerrada. Reabra la rendición para agregar comprobantes.",
        )
        return redirect("adm_rendicion_escritorio", pk=rendicion.pk)

    if request.method == "POST" and request.POST.get("accion") == "guardar":
        return _guardar_detalle_desde_ocr(request, rendicion)

    if request.method == "POST":
        form = SubirImagenComprobanteForm(request.POST, request.FILES)
        if form.is_valid():
            imagen = form.cleaned_data["imagen"]
            ext = os.path.splitext(imagen.name)[1].lower() or ".jpg"
            if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                ext = ".jpg"
            nombre_temp = f"{uuid.uuid4().hex}{ext}"
            ruta_temp = _tmp_dir() / nombre_temp
            with open(ruta_temp, "wb") as destino:
                for chunk in imagen.chunks():
                    destino.write(chunk)

            try:
                datos = extraer_datos_comprobante(str(ruta_temp))
            except Exception as exc:  # noqa: BLE001
                messages.error(request, f"Error al analizar la imagen: {exc}")
                if ruta_temp.exists():
                    ruta_temp.unlink()
                return redirect("adm_rendicion_agregar_comprobante", pk=rendicion.pk)

            inicial = {
                "rendicion_id": rendicion.pk,
                "imagen_temp": nombre_temp,
                "proveedor": datos.proveedor,
                "rut_proveedor": datos.rut_proveedor,
                "tipo_documento": datos.tipo_documento
                if datos.tipo_documento
                in dict(DetalleRendicion.TipoDocumento.choices)
                else DetalleRendicion.TipoDocumento.BOLETA,
                "numero_documento": datos.numero_documento,
                "sucursal": datos.sucursal,
                "fecha": datos.fecha,
                "descripcion": datos.descripcion or "Gasto desde comprobante",
                "forma_pago": datos.forma_pago
                if datos.forma_pago in dict(DetalleRendicion.FormaPago.choices)
                else DetalleRendicion.FormaPago.DEBITO,
                "neto": datos.neto or None,
                "iva": datos.iva or None,
                "total": datos.total or None,
            }
            return render(
                request,
                "administracion/rendicion_agregar_comprobante.html",
                {
                    "paso": "revisar",
                    "rendicion": rendicion,
                    "form_imagen": SubirImagenComprobanteForm(),
                    "form": ConfirmarDetalleComprobanteForm(initial=inicial),
                    "datos": datos,
                    "imagen_url": f"{settings.MEDIA_URL}administracion/tmp_ocr/{nombre_temp}",
                    **_contexto_progreso(rendicion),
                },
            )
        messages.error(request, "Revise la imagen subida.")

    return render(
        request,
        "administracion/rendicion_agregar_comprobante.html",
        {
            "paso": "subir",
            "rendicion": rendicion,
            "form_imagen": SubirImagenComprobanteForm(),
            **_contexto_progreso(rendicion),
        },
    )


def _guardar_detalle_desde_ocr(request, rendicion: Rendicion):
    form = ConfirmarDetalleComprobanteForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Complete los campos obligatorios (descripción y total).")
        nombre_temp = request.POST.get("imagen_temp", "")
        return render(
            request,
            "administracion/rendicion_agregar_comprobante.html",
            {
                "paso": "revisar",
                "rendicion": rendicion,
                "form_imagen": SubirImagenComprobanteForm(),
                "form": form,
                "datos": None,
                "imagen_url": (
                    f"{settings.MEDIA_URL}administracion/tmp_ocr/{nombre_temp}"
                    if nombre_temp
                    else ""
                ),
                **_contexto_progreso(rendicion),
            },
        )

    cleaned = form.cleaned_data
    if int(cleaned["rendicion_id"]) != rendicion.pk:
        messages.error(request, "La rendición no coincide.")
        return redirect("adm_rendicion_escritorio", pk=rendicion.pk)

    if rendicion.estado != Rendicion.Estado.BORRADOR:
        messages.error(request, "La carga de esta rendición ya fue cerrada.")
        return redirect("adm_rendicion_escritorio", pk=rendicion.pk)

    nombre_temp = cleaned["imagen_temp"]
    ruta_temp = _tmp_dir() / nombre_temp

    detalle = DetalleRendicion(
        rendicion=rendicion,
        fecha=cleaned["fecha"],
        tipo_documento=cleaned["tipo_documento"],
        numero_documento=cleaned["numero_documento"] or "",
        proveedor=cleaned["proveedor"] or "",
        rut_proveedor=cleaned["rut_proveedor"] or "",
        sucursal=cleaned["sucursal"] or "",
        descripcion=cleaned["descripcion"],
        forma_pago=cleaned["forma_pago"],
        neto=cleaned["neto"],
        iva=cleaned["iva"],
        total=cleaned["total"],
        justificacion_sin_documento=cleaned["justificacion_sin_documento"] or "",
        estado_revision=DetalleRendicion.EstadoRevision.PENDIENTE,
        creado_por=request.user,
    )

    if ruta_temp.exists():
        with open(ruta_temp, "rb") as fh:
            detalle.comprobante.save(nombre_temp, File(fh), save=False)

    detalle.full_clean()
    detalle.save()

    if ruta_temp.exists():
        ruta_temp.unlink(missing_ok=True)

    progreso = _contexto_progreso(rendicion)
    messages.success(
        request,
        f"Comprobante #{detalle.pk} guardado en la BD. "
        f"{progreso['cantidad_soportes']} soporte(s) — "
        f"suma ${progreso['suma_soportes']:,.0f}".replace(",", "."),
    )
    # Volver al escritorio; opción de seguir agregando desde ahí
    return redirect("adm_rendicion_escritorio", pk=rendicion.pk)


# Compatibilidad: URL antigua redirige a lista o escritorio
@login_required
def rendicion_desde_imagen(request):
    rid = request.GET.get("rendicion")
    if rid:
        return redirect("adm_rendicion_agregar_comprobante", pk=rid)
    return redirect("adm_rendicion_lista")


# ---------------------------------------------------------------------------
# Cerrar / reabrir / PDF
# ---------------------------------------------------------------------------

@login_required
@require_POST
def rendicion_finalizar_carga(request, pk):
    rendicion = get_object_or_404(Rendicion, pk=pk)
    if rendicion.estado != Rendicion.Estado.BORRADOR:
        messages.info(request, "La carga de comprobantes ya estaba cerrada.")
        return redirect("adm_rendicion_escritorio", pk=rendicion.pk)

    if not rendicion.detalles.exists():
        messages.error(
            request,
            "No hay comprobantes. Agregue al menos uno antes de cerrar.",
        )
        return redirect("adm_rendicion_escritorio", pk=rendicion.pk)

    hoy = timezone.localdate()
    rendicion.estado = Rendicion.Estado.PRESENTADA
    rendicion.fecha_presentacion = hoy
    dets = list(
        rendicion.detalles.exclude(
            estado_revision=DetalleRendicion.EstadoRevision.RECHAZADO
        ).values_list("fecha", flat=True)
    )
    if dets:
        rendicion.periodo_desde = min(dets)
        rendicion.periodo_hasta = max(dets)
    rendicion.actualizado_por = request.user
    rendicion.save()

    AprobacionRendicion.objects.create(
        rendicion=rendicion,
        accion=AprobacionRendicion.Accion.PRESENTADA,
        comentario=(
            f"Carga finalizada. {rendicion.detalles.count()} soporte(s), "
            f"total ${rendicion.total_rendido}."
        ),
        usuario=request.user,
        creado_por=request.user,
    )

    messages.success(
        request,
        f"Rendición {rendicion.numero}: carga terminada. "
        f"Total ${rendicion.total_rendido:,.0f}".replace(",", "."),
    )
    return redirect("adm_rendicion_escritorio", pk=rendicion.pk)


@login_required
@require_POST
def rendicion_reabrir_carga(request, pk):
    rendicion = get_object_or_404(Rendicion, pk=pk)
    if not _puede_editar_detalles(rendicion) and rendicion.estado != Rendicion.Estado.PRESENTADA:
        if rendicion.estado in (
            Rendicion.Estado.APROBADA,
            Rendicion.Estado.LIQUIDADA,
            Rendicion.Estado.CERRADA,
            Rendicion.Estado.ANULADA,
        ):
            messages.error(request, "Esta rendición no se puede reabrir.")
            return redirect("adm_rendicion_escritorio", pk=rendicion.pk)

    if rendicion.estado in (
        Rendicion.Estado.APROBADA,
        Rendicion.Estado.LIQUIDADA,
        Rendicion.Estado.CERRADA,
        Rendicion.Estado.ANULADA,
    ):
        messages.error(request, "Esta rendición no se puede reabrir.")
        return redirect("adm_rendicion_escritorio", pk=rendicion.pk)

    rendicion.estado = Rendicion.Estado.BORRADOR
    rendicion.fecha_presentacion = None
    rendicion.actualizado_por = request.user
    rendicion.save(
        update_fields=["estado", "fecha_presentacion", "actualizado_en", "actualizado_por"]
    )
    AprobacionRendicion.objects.create(
        rendicion=rendicion,
        accion=AprobacionRendicion.Accion.REABIERTA,
        comentario="Carga de comprobantes reabierta.",
        usuario=request.user,
        creado_por=request.user,
    )
    messages.info(request, "Carga reabierta: puede agregar o editar comprobantes.")
    return redirect("adm_rendicion_escritorio", pk=rendicion.pk)


@login_required
def rendicion_pdf(request, pk):
    rendicion = get_object_or_404(
        Rendicion.objects.select_related("responsable"), pk=pk
    )
    progreso = _contexto_progreso(rendicion)
    detalles_pdf = []
    for d in progreso["detalles"]:
        img_abs = ""
        if d.comprobante:
            img_abs = request.build_absolute_uri(d.comprobante.url)
        detalles_pdf.append({"obj": d, "imagen_abs": img_abs})

    html = render_to_string(
        "administracion/rendicion_pdf.html",
        {
            "rendicion": rendicion,
            "cantidad_soportes": progreso["cantidad_soportes"],
            "suma_soportes": progreso["suma_soportes"],
            "detalles": progreso["detalles"],
            "detalles_pdf": detalles_pdf,
            "generado_en": timezone.localtime(),
            "usuario": request.user,
        },
        request=request,
    )
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="rendicion-{rendicion.numero}.pdf"'
    )
    return response
