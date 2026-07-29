"""Formularios B001–B021. Activos: B001 bancos, B002 cuentas, B004 plantillas."""
from django import forms
from django.forms import inlineformset_factory
import re

from ..models import Banco, CampoMapeoCartola, CuentaBancaria, PlantillaMapeoCartola
from ..services.bancos import normalizar_codigo_banco, normalizar_nombre_banco


class BancoForm(forms.ModelForm):
    """B001 — alta / edición de bancos (sin mostrar la clave)."""

    class Meta:
        model = Banco
        fields = ["nombre", "codigo", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["codigo"].required = False
        self.fields["codigo"].help_text = "Opcional. Se normaliza a mayúsculas."

    def clean_nombre(self):
        nombre = normalizar_nombre_banco(self.cleaned_data.get("nombre") or "")
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        return nombre

    def clean_codigo(self):
        return normalizar_codigo_banco(self.cleaned_data.get("codigo") or "")


class ClaveCartolaForm(forms.Form):
    """
    B001 — definir / cambiar clave PDF de cartolas.
    Nunca muestra la clave actual; solo permite reemplazarla o borrarla.
    """

    clave_cartola = forms.CharField(
        label="Nueva clave de cartola",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
        required=False,
        help_text="Clave del PDF del banco. Queda cifrada en el sistema.",
    )
    clave_cartola_confirmacion = forms.CharField(
        label="Confirmar clave",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
        required=False,
    )
    limpiar = forms.BooleanField(
        label="Eliminar clave guardada",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    archivo_prueba = forms.FileField(
        label="PDF de prueba (opcional)",
        required=False,
        help_text="Si adjunta un PDF, se verifica que la nueva clave lo abre.",
    )

    def clean(self):
        cleaned = super().clean()
        limpiar = cleaned.get("limpiar")
        clave = (cleaned.get("clave_cartola") or "").strip()
        conf = (cleaned.get("clave_cartola_confirmacion") or "").strip()
        if limpiar:
            return cleaned
        if not clave and not conf:
            raise forms.ValidationError(
                "Indique la nueva clave o marque «Eliminar clave guardada»."
            )
        if clave != conf:
            raise forms.ValidationError("La clave y su confirmación no coinciden.")
        if len(clave) < 3:
            raise forms.ValidationError("La clave parece demasiado corta.")
        cleaned["clave_cartola"] = clave
        return cleaned


class CuentaBancariaForm(forms.ModelForm):
    """B002 — alta / edición de cuentas."""

    class Meta:
        model = CuentaBancaria
        fields = [
            "banco",
            "nombre",
            "numero_cuenta",
            "tipo_cuenta",
            "moneda",
            "titular",
            "rut_titular",
            "activa",
            "observaciones",
        ]
        labels = {
            "nombre": "Alias",
            "numero_cuenta": "Número de cuenta",
        }
        widgets = {
            "banco": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "numero_cuenta": forms.TextInput(attrs={"class": "form-control"}),
            "tipo_cuenta": forms.Select(attrs={"class": "form-select"}),
            "moneda": forms.TextInput(attrs={"class": "form-control"}),
            "titular": forms.TextInput(attrs={"class": "form-control"}),
            "rut_titular": forms.TextInput(attrs={"class": "form-control"}),
            "activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["banco"].queryset = Banco.objects.filter(activo=True).order_by(
            "nombre"
        )
        self.fields["titular"].required = False
        self.fields["rut_titular"].required = False
        self.fields["observaciones"].required = False
        self.fields["nombre"].help_text = "Alias interno (no es el nombre del banco)."

    def clean_nombre(self):
        nombre = re.sub(r"\s+", " ", (self.cleaned_data.get("nombre") or "").strip())
        if not nombre:
            raise forms.ValidationError("El alias es obligatorio.")
        return nombre

    def clean_numero_cuenta(self):
        from ..services.bancos import normalizar_numero_cuenta

        numero = normalizar_numero_cuenta(self.cleaned_data.get("numero_cuenta") or "")
        if not numero:
            raise forms.ValidationError("El número de cuenta es obligatorio.")
        return numero


class CargarCuentaDesdeCartolaForm(forms.Form):
    """B002 — precargar / crear cuenta leyendo un PDF de cartola."""

    banco = forms.ModelChoiceField(
        queryset=Banco.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Debe tener clave de cartola configurada (B001).",
    )
    archivo = forms.FileField(
        label="Cartola PDF",
        help_text="Se abre con la clave cifrada del banco. No crea movimientos.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["banco"].queryset = (
            Banco.objects.filter(activo=True)
            .exclude(clave_cartola_cifrada="")
            .order_by("nombre")
        )

    def clean_banco(self):
        banco = self.cleaned_data["banco"]
        if not banco.tiene_clave_cartola:
            raise forms.ValidationError(
                "Configure primero la clave de cartola en el banco."
            )
        return banco


class ImportarCartolaForm(forms.Form):
    """B003/B005 — importar o analizar duplicados de cartola PDF."""

    cuenta_bancaria = forms.ModelChoiceField(
        queryset=CuentaBancaria.objects.none(),
        label="Cuenta bancaria",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    archivo = forms.FileField(
        label="Cartola PDF",
        help_text="Se abre con la clave del banco. Use «Analizar» antes de importar.",
    )
    accion = forms.ChoiceField(
        choices=(
            ("analizar", "Analizar duplicados (no guarda)"),
            ("importar", "Importar y registrar movimientos"),
        ),
        initial="analizar",
        widget=forms.RadioSelect,
        label="Acción",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cuenta_bancaria"].queryset = (
            CuentaBancaria.objects.filter(activa=True, banco__activo=True)
            .exclude(banco__clave_cartola_cifrada="")
            .select_related("banco")
            .order_by("banco__nombre", "nombre")
        )


class PlantillaMapeoForm(forms.ModelForm):
    """B004 — identificación y estructura de la plantilla."""

    class Meta:
        model = PlantillaMapeoCartola
        fields = [
            "nombre",
            "banco",
            "cuenta_bancaria",
            "formato_archivo",
            "parser_codigo",
            "nombre_hoja",
            "fila_encabezado",
            "fila_inicio_datos",
            "separador_csv",
            "codificacion",
            "formato_fecha",
            "fecha_sin_anio",
            "separador_decimal",
            "separador_miles",
            "simbolo_moneda",
            "identificador_saldo_inicial",
            "identificador_saldo_final",
            "ignorar_filas_vacias",
            "activa",
            "observaciones",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "banco": forms.Select(attrs={"class": "form-select"}),
            "cuenta_bancaria": forms.Select(attrs={"class": "form-select"}),
            "formato_archivo": forms.Select(attrs={"class": "form-select"}),
            "nombre_hoja": forms.TextInput(attrs={"class": "form-control"}),
            "fila_encabezado": forms.NumberInput(attrs={"class": "form-control"}),
            "fila_inicio_datos": forms.NumberInput(attrs={"class": "form-control"}),
            "separador_csv": forms.TextInput(attrs={"class": "form-control"}),
            "codificacion": forms.TextInput(attrs={"class": "form-control"}),
            "formato_fecha": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "%d/%m/%Y"}
            ),
            "separador_decimal": forms.TextInput(attrs={"class": "form-control"}),
            "separador_miles": forms.TextInput(attrs={"class": "form-control"}),
            "ignorar_filas_vacias": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["banco"].queryset = Banco.objects.filter(activo=True).order_by(
            "nombre"
        )
        self.fields["cuenta_bancaria"].queryset = CuentaBancaria.objects.filter(
            activa=True
        ).select_related("banco")
        self.fields["cuenta_bancaria"].required = False
        self.fields["cuenta_bancaria"].empty_label = "— Todas las cuentas del banco —"
        self.fields["nombre"].required = True
        self.fields["nombre_hoja"].required = False
        self.fields["observaciones"].required = False
        self.fields["nombre_hoja"].help_text = "Solo XLSX. Vacío = hoja activa."
        self.fields["formato_fecha"].help_text = "Ej: %d/%m/%Y o %Y-%m-%d"

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        return nombre

    def clean(self):
        cleaned = super().clean()
        banco = cleaned.get("banco")
        cuenta = cleaned.get("cuenta_bancaria")
        if cuenta and banco and cuenta.banco_id != banco.pk:
            self.add_error(
                "cuenta_bancaria",
                "La cuenta debe pertenecer al banco seleccionado.",
            )
        return cleaned


class CampoMapeoForm(forms.ModelForm):
    class Meta:
        model = CampoMapeoCartola
        fields = [
            "campo_destino",
            "columna_origen",
            "obligatorio",
            "valor_defecto",
            "orden",
        ]
        widgets = {
            "campo_destino": forms.Select(attrs={"class": "form-select"}),
            "columna_origen": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombre columna cartola"}
            ),
            "obligatorio": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "valor_defecto": forms.TextInput(attrs={"class": "form-control"}),
            "orden": forms.NumberInput(
                attrs={"class": "form-control", "style": "width:5rem"}
            ),
        }


CampoMapeoFormSet = inlineformset_factory(
    PlantillaMapeoCartola,
    CampoMapeoCartola,
    form=CampoMapeoForm,
    extra=4,
    can_delete=True,
    min_num=3,
    validate_min=False,
)


class ProbarPlantillaForm(forms.Form):
    """B004 — archivo de muestra para previsualizar el mapeo."""

    archivo = forms.FileField(
        help_text="CSV o XLSX de ejemplo. No crea movimientos bancarios."
    )


class ClasificarMovimientoForm(forms.Form):
    """B008 — clasificación administrativa (no altera el dato bancario)."""

    categoria = forms.ChoiceField(
        label="Categoría",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    contraparte_normalizada = forms.CharField(
        label="Contraparte normalizada",
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="No reemplaza la contraparte original de la cartola.",
    )
    rut_contraparte_normalizado = forms.CharField(
        label="RUT normalizado",
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    observacion = forms.CharField(
        label="Observación",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        help_text="Obligatoria para categorías «OTRO» y al reclasificar conciliados.",
    )
    confirmar = forms.BooleanField(
        label="Confirmo la clasificación",
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, movimiento=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.movimiento = movimiento
        from ..models import ClasificacionMovimientoBancario

        if movimiento is not None:
            self.fields["categoria"].choices = (
                ClasificacionMovimientoBancario.categorias_para_tipo(
                    movimiento.tipo
                )
            )
            activa = movimiento.clasificacion_activa
            if activa and not self.is_bound:
                self.fields["categoria"].initial = activa.categoria
                self.fields[
                    "contraparte_normalizada"
                ].initial = activa.contraparte_normalizada
                self.fields[
                    "rut_contraparte_normalizado"
                ].initial = activa.rut_contraparte_normalizado

    def clean(self):
        cleaned = super().clean()
        from ..models import ClasificacionMovimientoBancario

        categoria = cleaned.get("categoria")
        observacion = (cleaned.get("observacion") or "").strip()
        if (
            categoria in ClasificacionMovimientoBancario.CATEGORIAS_OTRO
            and not observacion
        ):
            self.add_error(
                "observacion",
                "Las categorías «OTRO» requieren observación.",
            )
        cleaned["observacion"] = observacion
        cleaned["contraparte_normalizada"] = (
            cleaned.get("contraparte_normalizada") or ""
        ).strip()
        cleaned["rut_contraparte_normalizado"] = (
            cleaned.get("rut_contraparte_normalizado") or ""
        ).strip()
        return cleaned
