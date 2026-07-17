from django import forms
from django.utils import timezone

from .models import DetalleRendicion, Rendicion, ResponsableRendicion


class SubirComprobanteForm(forms.Form):
    imagen = forms.ImageField(
        label="Foto del comprobante",
        help_text="Foto clara de la boleta, ticket o voucher (JPG/PNG).",
    )
    rendicion = forms.ModelChoiceField(
        label="Rendición destino",
        queryset=Rendicion.objects.none(),
        required=False,
        empty_label="— Crear borrador automático —",
        help_text="Si no elige una, se crea una rendición en borrador para hoy.",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Rendicion.objects.exclude(
            estado__in=[Rendicion.Estado.CERRADA, Rendicion.Estado.ANULADA]
        ).order_by("-periodo_hasta", "-id")[:50]
        self.fields["rendicion"].queryset = qs
        self.fields["imagen"].widget.attrs.update(
            {
                "class": "form-control",
                "accept": "image/*",
                "capture": "environment",
            }
        )
        self.fields["rendicion"].widget.attrs.update({"class": "form-select"})


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
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.HiddenInput):
                continue
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} form-control".strip()


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


def get_or_create_rendicion_borrador(user, rendicion_id=None) -> Rendicion:
    if rendicion_id:
        return Rendicion.objects.get(pk=rendicion_id)

    responsable = get_or_create_responsable(user)
    hoy = timezone.localdate()
    numero = f"TMP-{hoy.strftime('%Y%m%d')}-{user.pk}"
    rendicion, _created = Rendicion.objects.get_or_create(
        numero=numero,
        defaults={
            "responsable": responsable,
            "periodo_desde": hoy,
            "periodo_hasta": hoy,
            "motivo": "Borrador desde fotos de comprobantes",
            "estado": Rendicion.Estado.BORRADOR,
            "creado_por": user,
        },
    )
    return rendicion
