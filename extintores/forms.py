from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Field
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.forms import inlineformset_factory, modelformset_factory
from django.utils.safestring import mark_safe
from django_summernote.widgets import SummernoteWidget
from .models import (
    Intervencion, DetalleIntervencion, Odt, DetalleOdt,
    Producto, ItemOdt, Cliente, CategoriaProducto, ImagenIntervencion,
    FactorAjusteCliente, ItemOdt, ItemIntervencion
)

### FORMULARIO PARA INTERVENCIÓN ###
class IntervencionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tecnico'].queryset = User.objects.filter(technician_profile__isnull=False)
        self.fields['tecnico'].label_from_instance = lambda obj: (
            f"{obj.get_full_name()} - {obj.technician_profile.specialization}"
        )

    con_odt = forms.BooleanField(
        label=mark_safe('<span style="color: #FF0000; font-weight: bold;">Click para Generar ODT</span>'),
        widget=forms.CheckboxInput(attrs={'class': 'con-odt-style'}),
        required=False
    )

    class Meta:
        model = Intervencion
        fields = ['cliente', 'tipo', 'fecha', 'tecnico','alias', 'notas','con_odt']
        widgets = {'fecha': forms.DateInput(attrs={'type': 'date'}),
                   'notas': SummernoteWidget(),
                                       
                    }

### FORMSET PARA IMÁGENES ###

class ImagenIntervencionForm(forms.ModelForm):
    class Meta:
        model = ImagenIntervencion
        fields = ['imagen1','imagen2','imagen3','imagen4','imagen5','imagen6','imagen7','imagen8','imagen9']
        labels = {
            'imagen1': 'Foto 1',
            'imagen2': 'Foto 2',
            'imagen3': 'Foto 3',
            'imagen4': 'Foto 4',
            'imagen5': 'Foto 5',
            'imagen6': 'Foto 6',
            'imagen7': 'Foto 7',
            'imagen8': 'Foto 8',
            'imagen9': 'Foto 9',
        }

ImagenIntervencionFormSet = modelformset_factory(
    ImagenIntervencion,
    form=ImagenIntervencionForm,
    extra=1,
    max_num=9,
    can_delete=True
)

### FORMULARIO DETALLES INTERVENCIÓN ###
### FORMULARIO DETALLES INTERVENCIÓN ###
class DetalleIntervencionForm(forms.ModelForm):
    class Meta:
        model = DetalleIntervencion
        fields = '__all__'
        widgets = {
            'ph_estado': forms.TextInput(attrs={'readonly': 'readonly'}),
            'ph_ultima': forms.DateInput(attrs={'type': 'date'}),
            'ph_vencimiento': forms.DateInput(attrs={'type': 'date', 'readonly': 'readonly'}),
            'ultima_fecha': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Marcar todos los BooleanField como no requeridos
        for field_name, field in self.fields.items():
            if isinstance(field, forms.BooleanField):
                field.required = False


DetalleIntervencionFormSet = inlineformset_factory(
    Intervencion,
    DetalleIntervencion,
    form=DetalleIntervencionForm,
    extra=0,
    can_delete=True,
    validate_min=False
)




### FORMULARIO ODT Y DETALLES ###
class OdtForm(forms.ModelForm):
    class Meta:
        model = Odt
        fields = ['alias','observaciones','estatus']
        widgets = {'observaciones': SummernoteWidget()}

class DetalleOdtForm(forms.ModelForm):
    class Meta:
        model = DetalleOdt
        fields = '__all__'
        #labels = {'ultima_fecha': 'Ultimo Mantenimiento fue:'}
        widgets = {
            'ph_estado': forms.TextInput(attrs={'readonly': 'readonly'}),
            'ph_ultima': forms.DateInput(attrs={'type': 'date'}),
            'ph_vencimiento': forms.DateInput(attrs={'type': 'date', 'readonly': 'readonly'}),
            'ultima_fecha': forms.DateInput(attrs={'type': 'date'}),
            
        }

        

DetalleOdtFormSet = inlineformset_factory(
    Odt,
    DetalleOdt,
    form=DetalleOdtForm,
    extra=0,
    can_delete=True
)

### FORMULARIOS PRODUCTOS Y CATEGORÍAS ###
class CategoriaForm(forms.ModelForm):
    class Meta:
        model = CategoriaProducto
        fields = ['nombre', 'componentes_relacionados']

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'precio_unitario','stock']

class ItemOdtForm(forms.ModelForm):
    class Meta:
        model = ItemOdt
        fields = ['producto', 'cantidad']

ItemOdtFormSet = inlineformset_factory(
    Odt,
    ItemOdt,
    form=ItemOdtForm,
    extra=0,
    can_delete=True
)

### FORMULARIO CLIENTE ###
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'rut', 'correo', 'direccion', 'comuna', 'telefono', 'contacto']
        widgets = {
            'correo': forms.EmailInput(attrs={'placeholder': 'ejemplo@dominio.com'})
        }


class FactorAjusteClienteForm(forms.ModelForm):
    class Meta:
        model = FactorAjusteCliente
        fields = ['cliente', 'categoria', 'factor']

class ItemIntervencionForm(forms.ModelForm):
    class Meta:
        model = ItemIntervencion
        fields = ['producto', 'cantidad']

ItemIntervencionFormSet = inlineformset_factory(
    Intervencion,
    ItemIntervencion,
    form=ItemIntervencionForm,
    extra=1,
    can_delete=True
)
