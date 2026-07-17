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
    SubirComprobanteForm,
    get_or_create_rendicion_borrador,
)
from .models import AprobacionRendicion, DetalleRendicion, Rendicion
from .ocr_comprobante import extraer_datos_comprobante


def _tmp_dir() -> Path:
    path = Path(settings.MEDIA_ROOT) / "administracion" / "tmp_ocr"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _contexto_progreso(rendicion: Rendicion | None) -> dict:
    if not rendicion:
        return {
            "rendicion_activa": None,
            "detalles": [],
            "cantidad_soportes": 0,
            "suma_soportes": Decimal("0.00"),
            "carga_abierta": False,
        }
    detalles = list(
        rendicion.detalles.exclude(
            estado_revision=DetalleRendicion.EstadoRevision.RECHAZADO
        ).order_by("fecha", "id")
    )
    agregados = rendicion.detalles.exclude(
        estado_revision=DetalleRendicion.EstadoRevision.RECHAZADO
    ).aggregate(cantidad=Count("id"), suma=Sum("total"))
    return {
        "rendicion_activa": rendicion,
        "detalles": detalles,
        "cantidad_soportes": agregados["cantidad"] or 0,
        "suma_soportes": agregados["suma"] or Decimal("0.00"),
        "carga_abierta": rendicion.estado == Rendicion.Estado.BORRADOR,
    }


def _resolver_rendicion_activa(request) -> Rendicion | None:
    rid = request.GET.get("rendicion") or request.session.get("adm_rendicion_activa")
    if not rid:
        return None
    try:
        return Rendicion.objects.select_related("responsable").get(pk=int(rid))
    except (Rendicion.DoesNotExist, ValueError, TypeError):
        return None


@login_required
@require_http_methods(["GET", "POST"])
def rendicion_desde_imagen(request):
    """
    Flujo de ingreso rápido:
      1) Subir foto del comprobante (o corregir a mano)
      2) Revisar datos OCR
      3) Guardar detalle y seguir sumando
      4) Terminar carga → estado PRESENTADA + ver resumen/PDF
    """
    if request.method == "POST" and request.POST.get("accion") == "guardar":
        return _guardar_detalle_desde_ocr(request)

    rendicion_activa = _resolver_rendicion_activa(request)
    progreso = _contexto_progreso(rendicion_activa)

    if request.method == "POST":
        form = SubirComprobanteForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            if progreso["carga_abierta"] is False and rendicion_activa:
                messages.warning(
                    request,
                    "Esta rendición ya cerró la carga de comprobantes. "
                    "Ábrala de nuevo o use otra rendición en borrador.",
                )
                return redirect(
                    "adm_rendicion_desde_imagen" + f"?rendicion={rendicion_activa.pk}"
                )

            imagen = form.cleaned_data["imagen"]
            rendicion = form.cleaned_data.get("rendicion") or rendicion_activa

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
                return redirect("adm_rendicion_desde_imagen")

            if rendicion:
                rendicion_obj = rendicion
            else:
                rendicion_obj = get_or_create_rendicion_borrador(request.user)

            request.session["adm_rendicion_activa"] = rendicion_obj.pk

            inicial = {
                "rendicion_id": rendicion_obj.pk,
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
            confirmar = ConfirmarDetalleComprobanteForm(initial=inicial)
            ctx = {
                "paso": "revisar",
                "form_subida": SubirComprobanteForm(
                    user=request.user, initial={"rendicion": rendicion_obj.pk}
                ),
                "form": confirmar,
                "datos": datos,
                "rendicion": rendicion_obj,
                "imagen_url": f"{settings.MEDIA_URL}administracion/tmp_ocr/{nombre_temp}",
            }
            ctx.update(_contexto_progreso(rendicion_obj))
            return render(request, "administracion/rendicion_desde_imagen.html", ctx)
        messages.error(request, "Revise la imagen subida.")
    else:
        initial = {}
        if rendicion_activa:
            initial["rendicion"] = rendicion_activa.pk
            request.session["adm_rendicion_activa"] = rendicion_activa.pk
        form = SubirComprobanteForm(user=request.user, initial=initial)

    ctx = {
        "paso": "subir",
        "form_subida": form,
    }
    ctx.update(progreso)
    return render(request, "administracion/rendicion_desde_imagen.html", ctx)


def _guardar_detalle_desde_ocr(request):
    form = ConfirmarDetalleComprobanteForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Complete los campos obligatorios (descripción y total).")
        nombre_temp = request.POST.get("imagen_temp", "")
        rendicion = get_object_or_404(
            Rendicion, pk=request.POST.get("rendicion_id") or 0
        )
        ctx = {
            "paso": "revisar",
            "form_subida": SubirComprobanteForm(
                user=request.user, initial={"rendicion": rendicion.pk}
            ),
            "form": form,
            "rendicion": rendicion,
            "imagen_url": (
                f"{settings.MEDIA_URL}administracion/tmp_ocr/{nombre_temp}"
                if nombre_temp
                else ""
            ),
            "datos": None,
        }
        ctx.update(_contexto_progreso(rendicion))
        return render(request, "administracion/rendicion_desde_imagen.html", ctx)

    cleaned = form.cleaned_data
    rendicion = get_object_or_404(Rendicion, pk=cleaned["rendicion_id"])

    if rendicion.estado != Rendicion.Estado.BORRADOR:
        messages.error(
            request,
            "No se pueden agregar comprobantes: la carga de esta rendición ya fue cerrada.",
        )
        return redirect("adm_rendicion_resumen", pk=rendicion.pk)

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

    request.session["adm_rendicion_activa"] = rendicion.pk
    progreso = _contexto_progreso(rendicion)

    messages.success(
        request,
        f"Comprobante #{detalle.pk} guardado. "
        f"Lleva {progreso['cantidad_soportes']} soporte(s) — "
        f"suma ${progreso['suma_soportes']:,.0f}".replace(",", "."),
    )
    return redirect(f"{reverse_adm_desde_imagen()}?rendicion={rendicion.pk}")


def reverse_adm_desde_imagen() -> str:
    from django.urls import reverse

    return reverse("adm_rendicion_desde_imagen")


@login_required
@require_POST
def rendicion_finalizar_carga(request, pk):
    """Marca el fin del ingreso de imágenes/soportes (BORRADOR → PRESENTADA)."""
    rendicion = get_object_or_404(Rendicion, pk=pk)
    if rendicion.estado != Rendicion.Estado.BORRADOR:
        messages.info(request, "La carga de comprobantes ya estaba cerrada.")
        return redirect("adm_rendicion_resumen", pk=rendicion.pk)

    if not rendicion.detalles.exists():
        messages.error(
            request,
            "No hay comprobantes cargados. Agregue al menos uno antes de cerrar.",
        )
        return redirect(f"{reverse_adm_desde_imagen()}?rendicion={rendicion.pk}")

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
            f"Carga de comprobantes finalizada. "
            f"{rendicion.detalles.count()} soporte(s), "
            f"total rendido ${rendicion.total_rendido}."
        ),
        usuario=request.user,
        creado_por=request.user,
    )

    messages.success(
        request,
        f"Rendición {rendicion.numero}: carga de comprobantes terminada. "
        f"Total ${rendicion.total_rendido:,.0f}".replace(",", "."),
    )
    return redirect("adm_rendicion_resumen", pk=rendicion.pk)


@login_required
@require_POST
def rendicion_reabrir_carga(request, pk):
    """Permite seguir agregando fotos si aún no está aprobada/cerrada."""
    rendicion = get_object_or_404(Rendicion, pk=pk)
    if rendicion.estado in (
        Rendicion.Estado.APROBADA,
        Rendicion.Estado.LIQUIDADA,
        Rendicion.Estado.CERRADA,
        Rendicion.Estado.ANULADA,
    ):
        messages.error(request, "Esta rendición no se puede reabrir para carga.")
        return redirect("adm_rendicion_resumen", pk=rendicion.pk)

    rendicion.estado = Rendicion.Estado.BORRADOR
    rendicion.fecha_presentacion = None
    rendicion.actualizado_por = request.user
    rendicion.save(update_fields=["estado", "fecha_presentacion", "actualizado_en", "actualizado_por"])
    AprobacionRendicion.objects.create(
        rendicion=rendicion,
        accion=AprobacionRendicion.Accion.REABIERTA,
        comentario="Carga de comprobantes reabierta.",
        usuario=request.user,
        creado_por=request.user,
    )
    request.session["adm_rendicion_activa"] = rendicion.pk
    messages.info(request, "Puede seguir agregando comprobantes.")
    return redirect(f"{reverse_adm_desde_imagen()}?rendicion={rendicion.pk}")


@login_required
def rendicion_resumen(request, pk):
    """Resumen en pantalla: lista, suma e imágenes de la rendición."""
    rendicion = get_object_or_404(
        Rendicion.objects.select_related("responsable"), pk=pk
    )
    ctx = {
        "rendicion": rendicion,
        **_contexto_progreso(rendicion),
        "diferencia_fondos": rendicion.total_fondos - rendicion.total_rendido,
    }
    return render(request, "administracion/rendicion_resumen.html", ctx)


@login_required
def rendicion_pdf(request, pk):
    """PDF resumen de la rendición con datos e imágenes de soportes."""
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
