from django import forms
from django.utils import timezone

from ..models import DetalleRendicion, Rendicion, ResponsableRendicion


class NuevaRendicionForm(forms.ModelForm):
    class Meta:
        model = Rendicion
        fields = ["motivo", "lugar_trabajo", "periodo_desde", "periodo_hasta", "observaciones"]
        widgets = {
            "motivo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Viáticos zona sur"}),
            "lugar_trabajo": forms.TextInput(attrs={"class": "form-control"}),
            "periodo_desde": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "periodo_hasta": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoy = timezone.localdate()
        self.fields["periodo_desde"].initial = hoy
        self.fields["periodo_hasta"].initial = hoy
        self.fields["motivo"].required = True


class SubirImagenComprobanteForm(forms.Form):
    """Solo imagen: la rendición ya está definida en la URL."""

    imagen = forms.ImageField(
        label="Foto del comprobante",
        help_text="Boleta, ticket o voucher (JPG/PNG).",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["imagen"].widget.attrs.update(
            {
                "class": "form-control",
                "accept": "image/*",
                "capture": "environment",
            }
        )


class ConfirmarDetalleComprobanteForm(forms.Form):
    rendicion_id = forms.IntegerField(widget=forms.HiddenInput)
    imagen_temp = forms.CharField(widget=forms.HiddenInput)

    proveedor = forms.CharField(max_length=150, required=False)
    rut_proveedor = forms.CharField(max_length=20, required=False)
    tipo_documento = forms.ChoiceField(choices=DetalleRendicion.TipoDocumento.choices)
    numero_documento = forms.CharField(max_length=60, required=False)
    sucursal = forms.CharField(max_length=100, required=False)
    fecha = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    descripcion = forms.CharField(max_length=255)
    forma_pago = forms.ChoiceField(choices=DetalleRendicion.FormaPago.choices)
    neto = forms.DecimalField(max_digits=14, decimal_places=2, required=False)
    iva = forms.DecimalField(max_digits=14, decimal_places=2, required=False)
    total = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    justificacion_sin_documento = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label="Justificación (si no hay documento)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _name, field in self.fields.items():
            if isinstance(field.widget, forms.HiddenInput):
                continue
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{css} form-control".strip()


class EditarDetalleRendicionForm(forms.ModelForm):
    class Meta:
        model = DetalleRendicion
        fields = [
            "fecha",
            "tipo_documento",
            "numero_documento",
            "proveedor",
            "rut_proveedor",
            "sucursal",
            "descripcion",
            "forma_pago",
            "neto",
            "iva",
            "total",
            "justificacion_sin_documento",
            "comprobante",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "tipo_documento": forms.Select(attrs={"class": "form-select"}),
            "numero_documento": forms.TextInput(attrs={"class": "form-control"}),
            "proveedor": forms.TextInput(attrs={"class": "form-control"}),
            "rut_proveedor": forms.TextInput(attrs={"class": "form-control"}),
            "sucursal": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.TextInput(attrs={"class": "form-control"}),
            "forma_pago": forms.Select(attrs={"class": "form-select"}),
            "neto": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "iva": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "total": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "justificacion_sin_documento": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "comprobante": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha"].widget = forms.DateInput(
            format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
        )
        self.fields["fecha"].input_formats = ["%Y-%m-%d"]


# Compatibilidad con código anterior
class SubirComprobanteForm(SubirImagenComprobanteForm):
    pass


def get_or_create_responsable(user) -> ResponsableRendicion:
    responsable = ResponsableRendicion.objects.filter(user=user).first()
    if responsable:
        return responsable
    nombre = user.get_full_name().strip() or user.username
    return ResponsableRendicion.objects.create(
        user=user,
        nombre=nombre,
        creado_por=user,
    )


def generar_numero_rendicion() -> str:
    hoy = timezone.localdate()
    prefijo = f"REND-{hoy.strftime('%Y%m%d')}-"
    ultimo = (
        Rendicion.objects.filter(numero__startswith=prefijo)
        .order_by("-numero")
        .values_list("numero", flat=True)
        .first()
    )
    if ultimo:
        try:
            seq = int(ultimo.rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = Rendicion.objects.filter(numero__startswith=prefijo).count() + 1
    else:
        seq = 1
    return f"{prefijo}{seq:03d}"


def crear_rendicion(user, cleaned_data) -> Rendicion:
    responsable = get_or_create_responsable(user)
    return Rendicion.objects.create(
        numero=generar_numero_rendicion(),
        responsable=responsable,
        periodo_desde=cleaned_data["periodo_desde"],
        periodo_hasta=cleaned_data["periodo_hasta"],
        motivo=cleaned_data.get("motivo") or "",
        lugar_trabajo=cleaned_data.get("lugar_trabajo") or "",
        observaciones=cleaned_data.get("observaciones") or "",
        estado=Rendicion.Estado.BORRADOR,
        creado_por=user,
    )


def get_or_create_rendicion_borrador(user, rendicion_id=None) -> Rendicion:
    """Legacy: preferir crear_rendicion / NuevaRendicionForm."""
    if rendicion_id:
        return Rendicion.objects.get(pk=rendicion_id)
    return crear_rendicion(
        user,
        {
            "periodo_desde": timezone.localdate(),
            "periodo_hasta": timezone.localdate(),
            "motivo": "Borrador automático",
            "lugar_trabajo": "",
            "observaciones": "",
        },
    )
