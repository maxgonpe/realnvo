"""Formularios X001–X013 (esqueleto)."""
from django import forms


class EmpresaFactoringForm(forms.Form):
    """X001 — TODO: ModelForm de EmpresaFactoring."""

    nombre = forms.CharField(max_length=150)


class OperacionFactoringForm(forms.Form):
    """X002 — TODO: ModelForm de OperacionFactoring."""

    referencia = forms.CharField(max_length=80)
