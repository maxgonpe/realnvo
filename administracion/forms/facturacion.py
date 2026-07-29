"""Formularios F001–F014 (esqueleto)."""
from django import forms


class FacturaVentaForm(forms.Form):
    """F002 — TODO: ModelForm de FacturaVenta."""

    numero = forms.CharField(max_length=40)
    monto_total = forms.DecimalField(max_digits=14, decimal_places=2)


class PagoClienteForm(forms.Form):
    """F005 — TODO: ModelForm de PagoCliente."""

    monto = forms.DecimalField(max_digits=14, decimal_places=2)


class GestionCobranzaForm(forms.Form):
    """F010 — TODO: ModelForm de GestionCobranza."""

    nota = forms.CharField(widget=forms.Textarea)
