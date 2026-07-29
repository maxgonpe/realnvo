"""
B001–B021 — Vistas de banco y conciliación.

Activos: B001 bancos (+ clave cartola), B004 plantillas.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms.bancos import (
    BancoForm,
    CampoMapeoFormSet,
    CargarCuentaDesdeCartolaForm,
    ClasificarMovimientoForm,
    ClaveCartolaForm,
    CuentaBancariaForm,
    ImportarCartolaForm,
    PlantillaMapeoForm,
    ProbarPlantillaForm,
)
from ..models import Banco, CuentaBancaria, ImportacionCartola, MovimientoBancario, PlantillaMapeoCartola
from ..services.clasificacion_movimientos import (
    clasificar_movimiento,
    historial_clasificaciones,
)
from ..selectors.bancos import (
    listar_bancos,
    listar_cuentas,
    listar_plantillas_mapeo,
    plantilla_con_campos,
    resumen_banco,
    resumen_cuenta,
    resumen_plantilla,
)
from ..services.bancos import (
    activar_banco,
    activar_cuenta,
    activar_plantilla,
    actualizar_banco,
    actualizar_cuenta,
    actualizar_plantilla,
    crear_banco,
    crear_cuenta,
    crear_cuenta_desde_cartola_pdf,
    crear_plantilla,
    definir_clave_cartola,
    desactivar_banco,
    desactivar_cuenta,
    desactivar_plantilla,
    limpiar_clave_cartola,
    previsualizar_plantilla,
    verificar_clave_contra_pdf,
)
from ..services.importacion_cartolas import analizar_cartola_pdf, importar_cartola_pdf
from ..services.duplicados import ArchivoDuplicadoError
from ._esqueleto import render_esqueleto


def _campos_desde_formset(formset) -> list[dict]:
    campos = []
    for form in formset.forms:
        if not hasattr(form, "cleaned_data"):
            continue
        data = form.cleaned_data
        if not data:
            continue
        campos.append(
            {
                "campo_destino": data.get("campo_destino"),
                "columna_origen": data.get("columna_origen"),
                "obligatorio": data.get("obligatorio", False),
                "valor_defecto": data.get("valor_defecto") or "",
                "orden": data.get("orden") or 0,
                "DELETE": data.get("DELETE", False),
            }
        )
    return campos


@login_required
def banco_lista(request):
    """B001 — Catálogo de bancos."""
    q = request.GET.get("q", "")
    estado = request.GET.get("estado", "todos")
    solo_activos = None
    if estado == "activos":
        solo_activos = True
    elif estado == "inactivos":
        solo_activos = False
    bancos = listar_bancos(q=q, solo_activos=solo_activos)
    return render(
        request,
        "administracion/bancos/banco_lista.html",
        {
            "bancos": bancos,
            "q": q,
            "estado": estado,
            "codigo_gantt": "B001",
            "titulo_esqueleto": "Catálogo de bancos",
        },
    )


@login_required
def banco_detalle(request, pk):
    """B001 — Detalle de banco + estado de clave cartola."""
    banco = get_object_or_404(Banco, pk=pk)
    return render(
        request,
        "administracion/bancos/banco_detalle.html",
        {
            "banco": banco,
            "resumen": resumen_banco(banco),
            "codigo_gantt": "B001",
        },
    )


@login_required
def banco_crear(request):
    """B001 — Alta de banco."""
    form = BancoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            banco = crear_banco(datos=form.cleaned_data, usuario=request.user)
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errs in exc.message_dict.items():
                    for err in errs:
                        form.add_error(field if field in form.fields else None, err)
            else:
                form.add_error(None, exc)
        else:
            messages.success(request, f"Banco «{banco.nombre}» creado.")
            return redirect("adm_banco_clave", pk=banco.pk)

    return render(
        request,
        "administracion/bancos/banco_form.html",
        {
            "form": form,
            "modo": "crear",
            "codigo_gantt": "B001",
            "titulo_esqueleto": "Nuevo banco",
        },
    )


@login_required
def banco_editar(request, pk):
    """B001 — Edición de banco."""
    banco = get_object_or_404(Banco, pk=pk)
    form = BancoForm(request.POST or None, instance=banco)
    if request.method == "POST" and form.is_valid():
        try:
            banco = actualizar_banco(
                banco=banco, datos=form.cleaned_data, usuario=request.user
            )
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errs in exc.message_dict.items():
                    for err in errs:
                        form.add_error(field if field in form.fields else None, err)
            else:
                form.add_error(None, exc)
        else:
            messages.success(request, f"Banco «{banco.nombre}» actualizado.")
            return redirect("adm_banco_detalle", pk=banco.pk)

    return render(
        request,
        "administracion/bancos/banco_form.html",
        {
            "form": form,
            "banco": banco,
            "modo": "editar",
            "codigo_gantt": "B001",
            "titulo_esqueleto": f"Editar — {banco.nombre}",
        },
    )


@login_required
def banco_clave(request, pk):
    """B001 — Definir / cambiar / borrar clave PDF de cartolas."""
    banco = get_object_or_404(Banco, pk=pk)
    form = ClaveCartolaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            if form.cleaned_data.get("limpiar"):
                limpiar_clave_cartola(banco=banco, usuario=request.user)
                messages.success(request, "Clave de cartola eliminada.")
            else:
                clave = form.cleaned_data["clave_cartola"]
                archivo = form.cleaned_data.get("archivo_prueba")
                definir_clave_cartola(banco=banco, clave=clave, usuario=request.user)
                if archivo:
                    archivo.seek(0)
                    if not verificar_clave_contra_pdf(banco=banco, archivo=archivo):
                        raise ValidationError(
                            "La clave se guardó, pero no abre el PDF de prueba. "
                            "Revísela con «Cambiar clave»."
                        )
                    messages.success(
                        request, "Clave guardada y verificada contra el PDF."
                    )
                else:
                    messages.success(request, "Clave de cartola guardada (cifrada).")
        except ValidationError as exc:
            messages.error(request, "; ".join(getattr(exc, "messages", [str(exc)])))
        else:
            return redirect("adm_banco_detalle", pk=banco.pk)

    return render(
        request,
        "administracion/bancos/banco_clave.html",
        {
            "banco": banco,
            "form": form,
            "codigo_gantt": "B001",
            "tiene_clave": banco.tiene_clave_cartola,
        },
    )


@login_required
@require_POST
def banco_activar(request, pk):
    banco = get_object_or_404(Banco, pk=pk)
    activar_banco(banco=banco, usuario=request.user)
    messages.success(request, f"Banco «{banco.nombre}» activado.")
    return redirect("adm_banco_detalle", pk=pk)


@login_required
@require_POST
def banco_desactivar(request, pk):
    banco = get_object_or_404(Banco, pk=pk)
    try:
        desactivar_banco(banco=banco, usuario=request.user)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, f"Banco «{banco.nombre}» desactivado.")
    return redirect("adm_banco_detalle", pk=pk)


@login_required
def cuenta_lista(request):
    """B002 — Lista de cuentas bancarias."""
    q = request.GET.get("q", "")
    estado = request.GET.get("estado", "todos")
    banco_id = request.GET.get("banco") or None
    solo_activas = None
    if estado == "activos":
        solo_activas = True
    elif estado == "inactivos":
        solo_activas = False
    cuentas = listar_cuentas(
        q=q,
        solo_activas=solo_activas,
        banco_id=int(banco_id) if banco_id else None,
    )
    return render(
        request,
        "administracion/bancos/cuenta_lista.html",
        {
            "cuentas": cuentas,
            "q": q,
            "estado": estado,
            "banco_id": banco_id or "",
            "bancos": Banco.objects.filter(activo=True).order_by("nombre"),
            "codigo_gantt": "B002",
        },
    )


@login_required
def cuenta_detalle(request, pk):
    """B002 — Detalle de cuenta."""
    cuenta = get_object_or_404(
        CuentaBancaria.objects.select_related("banco"), pk=pk
    )
    return render(
        request,
        "administracion/bancos/cuenta_detalle.html",
        {
            "cuenta": cuenta,
            "resumen": resumen_cuenta(cuenta),
            "codigo_gantt": "B002",
        },
    )


@login_required
def cuenta_crear(request):
    """B002 — Alta manual de cuenta."""
    form = CuentaBancariaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            cuenta = crear_cuenta(datos=form.cleaned_data, usuario=request.user)
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errs in exc.message_dict.items():
                    for err in errs:
                        form.add_error(field if field in form.fields else None, err)
            else:
                form.add_error(None, exc)
        else:
            messages.success(
                request, f"Cuenta «{cuenta.nombre}» ({cuenta.numero_cuenta}) creada."
            )
            return redirect("adm_cuenta_detalle", pk=cuenta.pk)

    return render(
        request,
        "administracion/bancos/cuenta_form.html",
        {
            "form": form,
            "modo": "crear",
            "codigo_gantt": "B002",
            "titulo_esqueleto": "Nueva cuenta bancaria",
        },
    )


@login_required
def cuenta_editar(request, pk):
    """B002 — Edición de cuenta."""
    cuenta = get_object_or_404(CuentaBancaria, pk=pk)
    form = CuentaBancariaForm(request.POST or None, instance=cuenta)
    if request.method == "POST" and form.is_valid():
        try:
            cuenta = actualizar_cuenta(
                cuenta=cuenta, datos=form.cleaned_data, usuario=request.user
            )
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errs in exc.message_dict.items():
                    for err in errs:
                        form.add_error(field if field in form.fields else None, err)
            else:
                form.add_error(None, exc)
        else:
            messages.success(request, f"Cuenta «{cuenta.nombre}» actualizada.")
            return redirect("adm_cuenta_detalle", pk=cuenta.pk)

    return render(
        request,
        "administracion/bancos/cuenta_form.html",
        {
            "form": form,
            "cuenta": cuenta,
            "modo": "editar",
            "codigo_gantt": "B002",
            "titulo_esqueleto": f"Editar — {cuenta.nombre}",
        },
    )


@login_required
def cuenta_desde_cartola(request):
    """B002 — Crear/actualizar cuenta leyendo metadatos de un PDF de cartola."""
    form = CargarCuentaDesdeCartolaForm(request.POST or None, request.FILES or None)
    meta = None
    if request.method == "POST" and form.is_valid():
        try:
            cuenta, meta = crear_cuenta_desde_cartola_pdf(
                banco=form.cleaned_data["banco"],
                archivo=form.cleaned_data["archivo"],
                usuario=request.user,
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request,
                f"Cuenta «{cuenta.nombre}» lista desde cartola "
                f"({cuenta.numero_enmascarado()}).",
            )
            return redirect("adm_cuenta_detalle", pk=cuenta.pk)

    return render(
        request,
        "administracion/bancos/cuenta_desde_cartola.html",
        {
            "form": form,
            "meta": meta,
            "codigo_gantt": "B002",
        },
    )


@login_required
@require_POST
def cuenta_activar(request, pk):
    cuenta = get_object_or_404(CuentaBancaria, pk=pk)
    try:
        activar_cuenta(cuenta=cuenta, usuario=request.user)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, f"Cuenta «{cuenta.nombre}» activada.")
    return redirect("adm_cuenta_detalle", pk=pk)


@login_required
@require_POST
def cuenta_desactivar(request, pk):
    cuenta = get_object_or_404(CuentaBancaria, pk=pk)
    try:
        desactivar_cuenta(cuenta=cuenta, usuario=request.user)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, f"Cuenta «{cuenta.nombre}» desactivada.")
    return redirect("adm_cuenta_detalle", pk=pk)


@login_required
def cartola_importar(request):
    """B003/B005 — Analizar duplicados o importar cartola PDF."""
    form = ImportarCartolaForm(request.POST or None, request.FILES or None)
    analisis = None
    archivo_duplicado = None

    if request.method == "POST" and form.is_valid():
        cuenta = form.cleaned_data["cuenta_bancaria"]
        archivo = form.cleaned_data["archivo"]
        accion = form.cleaned_data["accion"]
        try:
            if accion == "analizar":
                analisis = analizar_cartola_pdf(cuenta=cuenta, archivo=archivo)
                if analisis.get("archivo_duplicado"):
                    messages.warning(
                        request,
                        "ARCHIVO_DUPLICADO: esta cartola ya fue importada. "
                        "Revise el enlace al detalle anterior.",
                    )
                else:
                    messages.info(
                        request,
                        f"Análisis B005: {analisis['total_validos']} válidos, "
                        f"{analisis['total_duplicados_exactos']} duplicados exactos, "
                        f"{analisis['total_duplicados_en_archivo']} en archivo, "
                        f"{analisis['total_posibles']} posibles.",
                    )
            else:
                resultado = importar_cartola_pdf(
                    cuenta=cuenta, archivo=archivo, usuario=request.user
                )
                messages.success(
                    request,
                    f"Importados {resultado['importados']} movimientos "
                    f"({resultado['duplicados']} duplicados omitidos, "
                    f"{resultado.get('posibles', 0)} posibles con advertencia).",
                )
                return redirect(
                    "adm_cartola_detalle", pk=resultado["importacion"].pk
                )
        except ArchivoDuplicadoError as exc:
            archivo_duplicado = exc.importacion
            messages.error(request, str(exc))
        except ValidationError as exc:
            form.add_error(None, exc)

    recientes = (
        ImportacionCartola.objects.select_related(
            "cuenta_bancaria", "cuenta_bancaria__banco"
        )
        .order_by("-creado_en")[:10]
    )
    return render(
        request,
        "administracion/bancos/cartola_importar.html",
        {
            "form": form,
            "recientes": recientes,
            "analisis": analisis,
            "archivo_duplicado": archivo_duplicado,
            "codigo_gantt": "B005",
        },
    )


@login_required
def cartola_detalle(request, pk):
    """B003 — Detalle de importación / cartola."""
    importacion = get_object_or_404(
        ImportacionCartola.objects.select_related(
            "cuenta_bancaria", "cuenta_bancaria__banco", "plantilla"
        ),
        pk=pk,
    )
    cartola = getattr(importacion, "cartola", None)
    movimientos = (
        MovimientoBancario.objects.filter(importacion=importacion)
        .order_by("fecha_operacion", "id")
    )
    return render(
        request,
        "administracion/bancos/cartola_detalle.html",
        {
            "importacion": importacion,
            "cartola": cartola,
            "movimientos": movimientos,
            "codigo_gantt": "B003",
        },
    )


@login_required
def movimiento_lista(request):
    """B006 — Lista de movimientos bancarios."""
    q = request.GET.get("q", "")
    cuenta_id = request.GET.get("cuenta") or None
    qs = MovimientoBancario.objects.select_related(
        "cuenta_bancaria", "cuenta_bancaria__banco"
    ).order_by("-fecha_operacion", "-id")
    if cuenta_id:
        qs = qs.filter(cuenta_bancaria_id=int(cuenta_id))
    if q:
        from django.db.models import Q as DQ

        qs = qs.filter(
            DQ(descripcion_movimiento__icontains=q)
            | DQ(descripcion_original__icontains=q)
            | DQ(contraparte__icontains=q)
            | DQ(numero_documento__icontains=q)
        )
    return render(
        request,
        "administracion/bancos/movimiento_lista.html",
        {
            "movimientos": qs[:300],
            "q": q,
            "cuenta_id": cuenta_id or "",
            "cuentas": CuentaBancaria.objects.filter(activa=True).select_related("banco"),
            "codigo_gantt": "B006",
        },
    )


@login_required
def movimiento_detalle(request, pk):
    """B007 — Detalle de movimiento."""
    movimiento = get_object_or_404(
        MovimientoBancario.objects.select_related(
            "cuenta_bancaria", "cuenta_bancaria__banco", "importacion", "cartola"
        ),
        pk=pk,
    )
    clasificacion = movimiento.clasificacion_activa
    aplicaciones = movimiento.aplicaciones.filter(activa=True).order_by(
        "-fecha_aplicacion", "-id"
    )
    return render(
        request,
        "administracion/bancos/movimiento_detalle.html",
        {
            "movimiento": movimiento,
            "clasificacion": clasificacion,
            "aplicaciones": aplicaciones,
            "codigo_gantt": "B007",
        },
    )


@login_required
def movimiento_clasificar(request, pk):
    """B008 — Clasificación manual del movimiento."""
    movimiento = get_object_or_404(
        MovimientoBancario.objects.select_related(
            "cuenta_bancaria", "cuenta_bancaria__banco"
        ),
        pk=pk,
    )
    form = ClasificarMovimientoForm(
        request.POST or None, movimiento=movimiento
    )
    if request.method == "POST" and form.is_valid():
        try:
            clasif = clasificar_movimiento(
                movimiento_id=movimiento.pk,
                categoria=form.cleaned_data["categoria"],
                contraparte_normalizada=form.cleaned_data[
                    "contraparte_normalizada"
                ],
                rut_contraparte_normalizado=form.cleaned_data[
                    "rut_contraparte_normalizado"
                ],
                observacion=form.cleaned_data["observacion"],
                usuario=request.user,
            )
            messages.success(
                request,
                f"Clasificación guardada: {clasif.get_categoria_display()}",
            )
            return redirect("adm_movimiento_detalle", pk=movimiento.pk)
        except PermissionDenied as exc:
            form.add_error(None, str(exc))
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errs in exc.message_dict.items():
                    if field in form.fields:
                        for e in errs:
                            form.add_error(field, e)
                    else:
                        for e in errs:
                            form.add_error(None, e)
            else:
                form.add_error(None, exc)

    return render(
        request,
        "administracion/bancos/movimiento_clasificar.html",
        {
            "movimiento": movimiento,
            "form": form,
            "clasificacion": movimiento.clasificacion_activa,
            "codigo_gantt": "B008",
        },
    )


@login_required
def movimiento_historial_clasificaciones(request, pk):
    """B008 — Historial de clasificaciones del movimiento."""
    movimiento = get_object_or_404(
        MovimientoBancario.objects.select_related(
            "cuenta_bancaria", "cuenta_bancaria__banco"
        ),
        pk=pk,
    )
    return render(
        request,
        "administracion/bancos/movimiento_historial_clasificaciones.html",
        {
            "movimiento": movimiento,
            "historial": historial_clasificaciones(movimiento.pk),
            "codigo_gantt": "B008",
        },
    )


@login_required
def conciliacion_dashboard(request):
    """B018 — Dashboard de conciliación."""
    return render_esqueleto(
        request,
        "B018",
        "Dashboard de conciliación",
        "administracion/bancos/dashboard.html",
    )


@login_required
def plantilla_mapeo_lista(request):
    """B004 — Lista de plantillas de mapeo bancario."""
    q = request.GET.get("q", "")
    estado = request.GET.get("estado", "todos")
    banco_id = request.GET.get("banco") or None
    solo_activas = None
    if estado == "activos":
        solo_activas = True
    elif estado == "inactivos":
        solo_activas = False

    plantillas = listar_plantillas_mapeo(
        q=q,
        solo_activas=solo_activas,
        banco_id=int(banco_id) if banco_id else None,
    )
    return render(
        request,
        "administracion/bancos/plantilla_mapeo_lista.html",
        {
            "plantillas": plantillas,
            "q": q,
            "estado": estado,
            "banco_id": banco_id or "",
            "bancos": Banco.objects.filter(activo=True).order_by("nombre"),
            "codigo_gantt": "B004",
            "titulo_esqueleto": "Plantillas de mapeo bancario",
        },
    )


@login_required
def plantilla_mapeo_detalle(request, pk):
    """B004 — Detalle de plantilla."""
    plantilla = plantilla_con_campos(pk)
    return render(
        request,
        "administracion/bancos/plantilla_mapeo_detalle.html",
        {
            "plantilla": plantilla,
            "resumen": resumen_plantilla(plantilla),
            "codigo_gantt": "B004",
        },
    )


@login_required
def plantilla_mapeo_crear(request):
    """B004 — Alta de plantilla + campos."""
    form = PlantillaMapeoForm(request.POST or None)
    formset = CampoMapeoFormSet(request.POST or None, prefix="campos")

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            plantilla = crear_plantilla(
                datos=form.cleaned_data,
                campos=_campos_desde_formset(formset),
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
            messages.success(
                request, f"Plantilla «{plantilla.nombre}» v{plantilla.version} creada."
            )
            return redirect("adm_plantilla_mapeo_detalle", pk=plantilla.pk)

    return render(
        request,
        "administracion/bancos/plantilla_mapeo_form.html",
        {
            "form": form,
            "formset": formset,
            "modo": "crear",
            "codigo_gantt": "B004",
            "titulo_esqueleto": "Nueva plantilla de mapeo",
            "sin_bancos": not Banco.objects.filter(activo=True).exists(),
        },
    )


@login_required
def plantilla_mapeo_editar(request, pk):
    """B004 — Edición (o nueva versión si ya fue usada en importaciones)."""
    plantilla = get_object_or_404(
        PlantillaMapeoCartola.objects.select_related("banco", "cuenta_bancaria"),
        pk=pk,
    )
    form = PlantillaMapeoForm(request.POST or None, instance=plantilla)
    formset = CampoMapeoFormSet(
        request.POST or None, instance=plantilla, prefix="campos"
    )

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            resultado = actualizar_plantilla(
                plantilla=plantilla,
                datos=form.cleaned_data,
                campos=_campos_desde_formset(formset),
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
            if resultado.pk != plantilla.pk:
                messages.success(
                    request,
                    f"Se creó la versión {resultado.version} (la anterior quedó inactiva).",
                )
            else:
                messages.success(
                    request, f"Plantilla «{resultado.nombre}» actualizada."
                )
            return redirect("adm_plantilla_mapeo_detalle", pk=resultado.pk)

    return render(
        request,
        "administracion/bancos/plantilla_mapeo_form.html",
        {
            "form": form,
            "formset": formset,
            "plantilla": plantilla,
            "modo": "editar",
            "codigo_gantt": "B004",
            "titulo_esqueleto": f"Editar — {plantilla.nombre} v{plantilla.version}",
            "sin_bancos": False,
        },
    )


@login_required
@require_POST
def plantilla_mapeo_activar(request, pk):
    plantilla = get_object_or_404(PlantillaMapeoCartola, pk=pk)
    try:
        activar_plantilla(plantilla=plantilla, usuario=request.user)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, f"Plantilla «{plantilla.nombre}» activada.")
    return redirect("adm_plantilla_mapeo_detalle", pk=pk)


@login_required
@require_POST
def plantilla_mapeo_desactivar(request, pk):
    plantilla = get_object_or_404(PlantillaMapeoCartola, pk=pk)
    desactivar_plantilla(plantilla=plantilla, usuario=request.user)
    messages.success(request, f"Plantilla «{plantilla.nombre}» desactivada.")
    return redirect("adm_plantilla_mapeo_detalle", pk=pk)


@login_required
def plantilla_mapeo_probar(request, pk):
    """B004 — Previsualizar mapeo con archivo de muestra."""
    plantilla = plantilla_con_campos(pk)
    form = ProbarPlantillaForm(request.POST or None, request.FILES or None)
    preview = None

    if request.method == "POST" and form.is_valid():
        try:
            preview = previsualizar_plantilla(
                archivo=form.cleaned_data["archivo"],
                plantilla=plantilla,
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.info(
                request,
                f"Vista previa: {len(preview['filas'])} filas "
                f"de {preview['total_leidas']} leídas.",
            )

    return render(
        request,
        "administracion/bancos/plantilla_mapeo_probar.html",
        {
            "plantilla": plantilla,
            "form": form,
            "preview": preview,
            "codigo_gantt": "B004",
        },
    )
