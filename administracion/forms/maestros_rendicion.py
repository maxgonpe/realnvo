"""Formularios R003–R005, R010–R016."""
from django import forms
from django.contrib.auth import get_user_model

from ..models import ResponsableRendicion
from ..services.rendiciones import normalizar_rut

User = get_user_model()


class ResponsableRendicionForm(forms.ModelForm):
    """R003 — alta / edición de responsables."""

    class Meta:
        model = ResponsableRendicion
        fields = [
            "user",
            "nombre",
            "rut",
            "cargo",
            "area",
            "correo",
            "telefono",
            "activo",
            "observaciones",
        ]
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "rut": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "12.345.678-9"}
            ),
            "cargo": forms.TextInput(attrs={"class": "form-control"}),
            "area": forms.TextInput(attrs={"class": "form-control"}),
            "correo": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.order_by("username")
        self.fields["user"].required = False
        self.fields["user"].empty_label = "— Sin usuario de sistema —"
        self.fields["nombre"].required = True
        for name in ("rut", "cargo", "area", "correo", "telefono", "observaciones"):
            self.fields[name].required = False

    def clean_rut(self):
        return normalizar_rut(self.cleaned_data.get("rut") or "")

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        return nombre


class CategoriaGastoForm(forms.Form):
    """R004 — TODO: ModelForm de CategoriaGasto."""

    nombre = forms.CharField(max_length=120)


class EntregaFondoForm(forms.Form):
    """R005 — TODO: ModelForm de EntregaFondo."""

    monto = forms.DecimalField(max_digits=14, decimal_places=2)
    fecha = forms.DateField()


class PresentarRendicionForm(forms.Form):
    """R010 — confirmación de presentación."""

    confirmar = forms.BooleanField(required=True)


class ObservacionGastoForm(forms.Form):
    """R011 — observación por detalle."""

    observacion = forms.CharField(widget=forms.Textarea)


class LiquidacionRendicionForm(forms.Form):
    """R014 — TODO: ModelForm / servicio de liquidación."""

    observaciones = forms.CharField(required=False, widget=forms.Textarea)
