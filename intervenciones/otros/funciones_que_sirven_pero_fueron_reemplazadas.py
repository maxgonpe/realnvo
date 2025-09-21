class OdtListViewOriginal(ListView):
    model = Odt
    template_name = 'odt/lista.html'
    context_object_name = 'odts'

def editar_odt_propuesta(request, pk):
    odt = get_object_or_404(Odt, pk=pk)
    
    # Lógica de detección de componentes defectuosos
    componentes = {
        'exterior': 'exterior',
        'valvula': 'Válvula',
        'manometro': 'Manómetro',
        'manguera': 'Manguera',
        'cintillo': 'Cintillo',
        'agente_extintor': 'Agente Extintor',
        'tubo_sifon': 'Tubo Sifón',
        'sellos_seguro': 'Sellos de Seguridad',
        'seguridad': 'Sistema de Seguridad',
        'rotulacion': 'Rotulación',
        'recarga': 'recarga',
        'mantencion': 'mantencion',
        'correcta': 'Estado General',
        'acceso': 'Acceso',
        'instrucciones': 'Instrucciones'
    }
    
    sugerencias = []
    for detalle in odt.detalles.all():
        problemas = []
        for campo, nombre in componentes.items():
            if getattr(detalle, campo) == False:
                problemas.append(nombre)
        
        if problemas:
            productos_sugeridos = Producto.objects.filter(
                Q(nombre__icontains='extintor') |
                Q(categoria__nombre__in=['Partes', 'Repuestos', 'Componentes'])
            ).distinct()
            
            sugerencias.append({
                'extintor': detalle,
                'problemas': problemas,
                'productos': productos_sugeridos
            })

    if request.method == 'POST':
        # ... lógica existente ...
        pass
    else:
        # ... lógica existente ...
        pass

    return render(request, 'odt/editar.html', {
        'form': form,
        'formset': formset,
        'itemset': itemset,
        'odt': odt,
        'sugerencias': sugerencias  # <-- Añadir esto
    })

def editar_odt_original(request, pk):
    odt = get_object_or_404(Odt, pk=pk)

    if request.method == 'POST':
        form = OdtForm(request.POST, instance=odt)
        formset = DetalleOdtFormSet(request.POST, instance=odt, prefix='detalleodt')
        itemset = ItemOdtFormSet(request.POST, instance=odt, prefix='itemodt')

        if form.is_valid() and formset.is_valid() and itemset.is_valid():
            form.save()
            formset.save()
            itemset.save()
            return redirect('odt_lista')
    else:
        form = OdtForm(instance=odt)
        formset = DetalleOdtFormSet(instance=odt, prefix='detalleodt')
        itemset = ItemOdtFormSet(instance=odt, prefix='itemodt')

    return render(request, 'odt/editar.html', {
        'form': form,
        'formset': formset,
        'itemset': itemset,
        'odt': odt,
                
    })


class IntervencionListViewOriginal(LoginRequiredMixin, ListView):
    model = Intervencion
    template_name = 'intervenciones/lista.html'
    context_object_name = 'intervenciones'

    def get_queryset(self):
        return Intervencion.objects.all().order_by('-id')


def crear_intervencion_revento(request):
    prefix = 'detalles'
    if request.method == 'POST':
        form = IntervencionForm(request.POST)
        formset = DetalleIntervencionFormSet(request.POST)
        imagenes_form = ImagenIntervencionForm(request.POST, request.FILES)

        
        if form.is_valid() and formset.is_valid() and imagenes_form.is_valid():
            intervencion = form.save()
            formset.save()

            imagen_instance = imagenes_form.save(commit=False)
            imagen_instance.intervencion = intervencion  # Asignar intervención antes de guardar
            imagen_instance.save()


            ImagenIntervencion.objects.create(
                intervencion=intervencion,
                imagen1=imagenes_form.cleaned_data.get('imagen1'),
                imagen2=imagenes_form.cleaned_data.get('imagen2'),
                imagen3=imagenes_form.cleaned_data.get('imagen3'),
                imagen4=imagenes_form.cleaned_data.get('imagen4'),
                imagen5=imagenes_form.cleaned_data.get('imagen5'),
                imagen6=imagenes_form.cleaned_data.get('imagen6'),
            )

            if intervencion.con_odt and not hasattr(intervencion, 'odt_rel'):
                odt = Odt.objects.create(intervencion=intervencion,tecnico=intervencion.tecnico)
                for d in intervencion.detalles.all():
                    DetalleOdt.objects.create(
                        odt=odt,
                        agente=d.agente,
                        nro_precinto=d.nro_precinto,
                        ubicacion=d.ubicacion,
                        sello_incen=d.sello_incen,
                        sello_incen_ste=d.sello_incen_ste,
                        certificado=d.certificado,
                        estado=d.estado,
                        exterior=d.exterior,
                        ph_ultima=d.ph_ultima,
                        ph_estado=d.ph_estado,
                        ph_vencimiento=d.ph_vencimiento,
                        valvula=d.valvula,
                        manometro=d.manometro,
                        manguera=d.manguera,
                        cintillo=d.cintillo,
                        agente_extintor=d.agente_extintor,
                        tubo_sifon=d.tubo_sifon,
                        sellos_seguro=d.sellos_seguro,
                        seguridad=d.seguridad,
                        rotulacion=d.rotulacion,
                        ultima_fecha=d.ultima_fecha,
                        recarga=d.recarga,
                        mantencion=d.mantencion,
                        presion=d.presion,
                        peso=d.peso,
                        correcta=d.correcta,
                        acceso=d.acceso,
                        instrucciones=d.instrucciones,
                    )

            return redirect('intervencion_lista')
    else:
        form = IntervencionForm()
        formset = DetalleIntervencionFormSet(prefix=prefix)
        imagenes_form = ImagenIntervencionForm()

    registrar_bitacora(
                usuario=self.request.user,
                accion='Crear una Intervención',
                modelo='Intervencion',
                objeto_id=odt,
                descripcion=f'El usuario {self.request.user} creo una nueva intervencion con el identificador .'
            )

    return render(request, 'intervenciones/crear.html', {
        'form': form,
        'formset': formset,
        'imagenes_form': imagenes_form,
        'prefix': prefix
    })


def editar_intervencionEnProduccion(request, pk):
    intervencion = get_object_or_404(Intervencion, pk=pk)
    prefix = 'detalles'
    imagenes_instance = ImagenIntervencion.objects.filter(intervencion=intervencion).first()

    if request.method == 'POST':

        print("Método de la solicitud:", request.method)
        form = IntervencionForm(request.POST, instance=intervencion)
        formset = DetalleIntervencionFormSet(request.POST, instance=intervencion, prefix=prefix)
        imagenes_form = ImagenIntervencionForm(request.POST, request.FILES, instance=imagenes_instance)

        if form.is_valid() and formset.is_valid() and imagenes_form.is_valid():
            intervencion = form.save()
            formset.save()

            imagen_instance = imagenes_form.save(commit=False)
            imagen_instance.intervencion = intervencion  # Asignar intervención antes de guardar
            imagen_instance.save()

            if intervencion.con_odt and not hasattr(intervencion, 'odt_rel'):
                odt = Odt.objects.create(intervencion=intervencion,tecnico=intervencion.tecnico)
                for d in intervencion.detalles.all():
                    DetalleOdt.objects.create(
                        odt=odt,
                        agente=d.agente,
                        nro_precinto=d.nro_precinto,
                        ubicacion=d.ubicacion,
                        sello_incen=d.sello_incen,
                        sello_incen_ste=d.sello_incen_ste,
                        certificado=d.certificado,
                        estado=d.estado,
                        exterior=d.exterior,
                        ph_ultima=d.ph_ultima,
                        ph_estado=d.ph_estado,
                        ph_vencimiento=d.ph_vencimiento,
                        valvula=d.valvula,
                        manometro=d.manometro,
                        manguera=d.manguera,
                        cintillo=d.cintillo,
                        agente_extintor=d.agente_extintor,
                        tubo_sifon=d.tubo_sifon,
                        sellos_seguro=d.sellos_seguro,
                        seguridad=d.seguridad,
                        rotulacion=d.rotulacion,
                        ultima_fecha=d.ultima_fecha,
                        recarga=d.recarga,
                        mantencion=d.mantencion,
                        presion=d.presion,
                        peso=d.peso,
                        correcta=d.correcta,
                        acceso=d.acceso,
                        instrucciones=d.instrucciones,
                    )

                registrar_bitacora(
                        usuario=request.user,
                        accion='Crear',
                        modelo='Odt',
                        objeto_id=pk,
                        descripcion = f"El usuario {request.user.username} creo la Odt #{odt.pk} con fecha {odt.fecha.strftime('%Y-%m-%d')}."
                        
                    )

            return redirect('intervencion_lista')
    else:
        form = IntervencionForm(instance=intervencion)
        formset = DetalleIntervencionFormSet(instance=intervencion, prefix=prefix)
        imagenes_form = ImagenIntervencionForm(instance=imagenes_instance)

    registrar_bitacora(
                usuario=request.user,
                accion='Modificar una Intervención',
                modelo='Intervencion',
                objeto_id=pk,
                descripcion= f"El usuario {request.user.username} edito y modifico la intervención #{intervencion.pk} con fecha {intervencion.fecha.strftime('%Y-%m-%d')}."
                
            )


    return render(request, 'intervenciones/editar.html', {
        'form': form,
        'formset': formset,
        'imagenes_form': imagenes_form,
        'intervencion': intervencion,
        'prefix': prefix
    })


class IntervencionExcelSimple(View):
    def get(self, request, pk):
        intervencion = Intervencion.objects.get(pk=pk)
        detalles = intervencion.detalles.all().order_by('id')

        wb = Workbook()
        ws = wb.active

        # Encabezado
        ws['A1'] = f'PLANILLA DE {intervencion.get_tipo_display().upper()}'
        ws['A2'] = f'Cliente: {intervencion.cliente}'
        ws['C2'] = f'Técnico: {intervencion.tecnico}'
        ws['E2'] = f'Fecha: {intervencion.fecha}'
        ws.merge_cells('A1:H1')

        # Títulos
        headers = [
            'N°', 'Agente','Nro Precinto','Ubicación', 'Sello INCEN','Sello INCEN STE', 'Certificado','Estado', 'Cilindro  Exterior','Ultima PH', 'Estado PH',\
            'Vencimiento PH','Valvula','Manometro','Manguera','Cintillo','Agente Extintor','Tubo Sifon', 'Sellos Seguro', 'Dispositivo Seguridad', 'Rotulacion',\
            'Ult Fecha Mantto.', 'Recarga', 'Mantencion', 'Presion', 'Peso', 'Inst Correcta', 'Acceso', 'Instrucciones'
        ]
        for col_num, header in enumerate(headers, 1):
            ws.cell(row=4, column=col_num).value = header

        # Filas
        row = 5
        for idx, d in enumerate(detalles, 1):
            ws.cell(row=row, column=1).value = idx
            ws.cell(row=row, column=2).value = d.agente
            ws.cell(row=row, column=3).value = d.nro_precinto
            ws.cell(row=row, column=4).value = d.ubicacion
            ws.cell(row=row, column=5).value = d.sello_incen
            ws.cell(row=row, column=6).value = d.sello_incen_ste
            ws.cell(row=row, column=7).value = d.certificado
            ws.cell(row=row, column=8).value = d.estado
            ws.cell(row=row, column=9).value = "OK" if d.exterior else "X"
            ws.cell(row=row, column=10).value = d.ph_ultima
            ws.cell(row=row, column=11).value = d.ph_estado
            ws.cell(row=row, column=12).value = d.ph_vencimiento
            ws.cell(row=row, column=13).value = "OK" if d.valvula else "X"
            ws.cell(row=row, column=14).value = "OK" if d.manguera else "X"
            ws.cell(row=row, column=15).value = "OK" if d.manometro else "X"
            ws.cell(row=row, column=16).value = "OK" if d.cintillo else "X"
            ws.cell(row=row, column=17).value = "OK" if d.agente_extintor else "X"
            ws.cell(row=row, column=18).value = "OK" if d.tubo_sifon else "X"
            ws.cell(row=row, column=19).value = "OK" if d.sellos_seguro else "X"
            ws.cell(row=row, column=20).value = "OK" if d.seguridad else "X"
            ws.cell(row=row, column=21).value = "OK" if d.rotulacion else "X"
            ws.cell(row=row, column=22).value = d.ultima_fecha.strftime('%Y-%m-%d') if d.ultima_fecha else ''
            ws.cell(row=row, column=23).value = "OK" if d.recarga else "X"
            ws.cell(row=row, column=24).value = "OK" if d.mantencion else "X"
            ws.cell(row=row, column=25).value = d.presion
            ws.cell(row=row, column=26).value = d.peso
            ws.cell(row=row, column=27).value = "OK" if d.correcta else "X"
            ws.cell(row=row, column=28).value = "OK" if d.acceso else "X"
            ws.cell(row=row, column=29).value = "OK" if d.instrucciones else "X"
      
            row += 1

        # Nombre y respuesta
        nombre_archivo = f"{intervencion.get_tipo_display()}-{intervencion.pk}.xlsx"
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
        wb.save(response)
        return response

class IntervencionPDFAntesPropuesta(View):
    def get(self, request, pk):
        intervencion = Intervencion.objects.select_related(
            'tecnico', 'tecnico__technician_profile'
        ).get(pk=pk)
        detalles = intervencion.detalles.all().order_by('id')
        imagenes = intervencion.imagenes.first()  # accede a ImagenIntervencion

        html_string = render_to_string('intervenciones/pdf_intervencion.html', {
            'intervencion': intervencion,
            'detalles': detalles,
            'imagenes': imagenes,
        })

        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf_file = html.write_pdf(stylesheets=[CSS(string='@page { size: landscape; }')])

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Intervencion-{pk}.pdf"'
        return response


class IntervencionPDFBuena(View):
    def get(self, request, pk):
        #intervencion = Intervencion.objects.get(pk=pk)
        intervencion = Intervencion.objects.select_related(
        'tecnico', 'tecnico__technician_profile').get(pk=pk)
        detalles = intervencion.detalles.all().order_by('id')

        # Renderiza el HTML del template
        html_string = render_to_string('intervenciones/pdf_intervencion.html', {
            'intervencion': intervencion,
            'detalles': detalles
        })

        # Genera el PDF desde HTML usando WeasyPrint
        html = HTML(string=html_string)
        #pdf_file = html.write_pdf()
        # Forzamos orientación horizontal
        pdf_file = html.write_pdf(stylesheets=[CSS(string='@page { size: landscape; }')])

        # Retorna la respuesta como archivo PDF descargable
        response = HttpResponse(pdf_file, content_type='application/pdf')
        #response['Content-Disposition'] = f'attachment; filename="Intervencion-{pk}.pdf"'
        response['Content-Disposition'] = f'inline; filename="Intervencion-{pk}.pdf"'
        return response


class IntervencionPDFSimple(View):
    def get(self, request, pk):
        intervencion = Intervencion.objects.get(pk=pk)
        detalles = intervencion.detalles.all().order_by('id')

        html_string = render_to_string('intervenciones/pdf_intervencion.html', {
            'intervencion': intervencion,
            'detalles': detalles
        })

        html = HTML(string=html_string)
        pdf_file = html.write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Intervencion-{pk}.pdf"'
        return response




def odt_detalle_original(request, pk):
    odt = get_object_or_404(Odt, pk=pk)
    total = odt.items.aggregate(total=Sum(F('cantidad') * F('producto__precio_unitario')))['total'] or 0
    return render(request, 'odt/detalle.html', {'odt': odt,'total': total})


def odt_pdf_original(request, pk):
    odt = Odt.objects.get(pk=pk)
    total = sum([item.subtotal for item in odt.items.all()])
    template = get_template('odt/pdf.html')
    html_content = template.render({"odt": odt, "total": total})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ODT-{odt.pk}.pdf"' 
    HTML(string=html_content).write_pdf(response)
    return response


class DetalleIntervencionFormConCryspy(forms.ModelForm):
    class Meta:
        model = DetalleIntervencion
        fields = '__all__'
        widgets = {
            'ph_estado': forms.TextInput(attrs={'readonly': 'readonly'}),
            'costo_materiales': forms.TextInput(attrs={'readonly': 'readonly'}),
            'ph_ultima': forms.DateInput(attrs={'type': 'date'}),
            'ph_vencimiento': forms.DateInput(attrs={'type': 'date', 'readonly': 'readonly'}),
            'ultima_fecha': forms.DateInput(attrs={'type': 'date'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False  # Porque el formulario principal ya lo tiene en el template

        self.helper.layout = Layout(
            # Campos generales que puedes ajustar según orden
            Row(
                Column('agente', css_class='form-group col-md-6'),
                Column('nro_precinto', css_class='form-group col-md-6'),
            ),
            'ubicacion',
            'sello_incen',
            'sello_incen_ste',
            'certificado',
            'estado',
            'exterior',
            Fieldset(
                'Condiciones Especiales',
                Row(
                    Column('habilitado_un_anox', css_class='form-check col-md-4'),
                    Column('baja_por_oxido', css_class='form-check col-md-4'),
                    Column('baja_por_ph', css_class='form-check col-md-4'),
                ),
                css_class='bg-light p-3 border rounded'
            ),
            Row(
                Column('ph_ultima', css_class='form-group col-md-4'),
                Column('ph_estado', css_class='form-group col-md-4'),
                Column('ph_vencimiento', css_class='form-group col-md-4'),
            ),
            'valvula',
            'manometro',
            'manguera',
            'cintillo',
            'agente_extintor',
            'tubo_sifon',
            'sellos_seguro',
            'seguridad',
            'rotulacion',
            'ultima_fecha',
            'recarga',
            'mantencion',
            'presion',
            'peso',
            'correcta',
            'acceso',
            'instrucciones',
        )


class DetalleIntervencionFormPropuesta(forms.ModelForm):
    class Meta:
        model = DetalleIntervencion
        fields = '__all__'
        widgets = {
            'ph_estado': forms.TextInput(attrs={'readonly': 'readonly'}),
            'costo_materiales': forms.TextInput(attrs={'readonly': 'readonly'}),
            'ph_ultima': forms.DateInput(attrs={'type': 'date'}),
            'ph_vencimiento': forms.DateInput(attrs={'type': 'date', 'readonly': 'readonly'}),
            'ultima_fecha': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False  # Porque ya estás usando el formulario en tu template
        self.helper.layout = Layout(
            # Aquí puedes incluir los campos normalmente o en filas
            Row(
                Column('agente', css_class='form-group col-md-6 mb-0'),
                Column('nro_precinto', css_class='form-group col-md-6 mb-0'),
            ),
            'ubicacion',
            'sello_incen',
            # ... otros campos

            # 👉 Aquí destacamos los campos nuevos en una sección
            Fieldset(
                'Estado del Extintor / Baja',
                Row(
                    Column('habilitado_un_ano', css_class='form-check col-md-4'),
                    Column('baja_por_oxido', css_class='form-check col-md-4'),
                    Column('baja_por_ph', css_class='form-check col-md-4'),
                ),
                css_class='bg-light p-3 border rounded'
            ),

            # Luego puedes seguir con los demás campos
            'ph_ultima',
            'ph_estado',
            'ph_vencimiento',
        )


odt,
{'agent',
'nro_precinto',
'ubicacion',
'sello_incen',
'sello_incen_ste',
'certificado',
'estado',
'exterior',
'ph_ultima',
'ph_estado',
'ph_vencimiento',
'valvula',
'manometro',
'manguera',
'cintillo',
'agente_extintor',
'tubo_sifon',
'sellos_seguro',
'seguridad',
'rotulacion',
'ultima_fecha',
'recarga',
'mantencion',
'presion',
'peso',
'correcta',
'acceso',
'instrucciones',
'habilitado_un_ano',
'baja_por_oxido',
'baja_por_ph'
}
agent,nro_precinto,ubicacion,sello_incen,sello_incen_ste,
certificado,estado,exterior,ph_ultima,ph_estado,ph_vencimiento,
valvula,manometro,manguera,cintillo,agente_extintor,tubo_sifon,
sellos_seguro,seguridad,rotulacion,ultima_fecha,recarga,mantencion,
presion,peso,correcta,acceso,instrucciones,habilitado_un_ano,
baja_por_oxido,baja_por_ph

['agente',
                'nro_precinto',
                'ubicacion',
                'sello_incen',
                'sello_incen_ste',
                'certificado',
                'estado',
                'exterior',
                'ph_ultima',
                'ph_estado',
                'ph_vencimiento',
                'valvula',
                'manometro',
                'manguera',
                'cintillo',
                'agente_extintor',
                'tubo_sifon',
                'sellos_seguro',
                'seguridad',
                'rotulacion',
                'ultima_fecha',
                'recarga',
                'mantencion',
                'presion',
                'peso',
                'correcta',
                'acceso',
                'instrucciones',
                'habilitado_un_ano',
                'baja_por_oxido',
                'baja_por_ph',
                ]


{% extends 'base.html' %}
{% load crispy_forms_tags %}

{% block content %}
<h2>Editar Servicio  #{{ intervencion.pk }}</h2>

<style>
    .counter-badge {
        background-color: #007bff;
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.9em;
        margin-right: 10px;
    }
</style>

<form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    {{ form|crispy }}
    {{ formset.management_form }}

    <div id="form-container">
        {% for form in formset %}
            <div class="card mt-3 p-3" style="background-color: #DCDCDC;" data-form-index="{{ forloop.counter0 }}">
                <h5 class="mb-3">
                    <span class="counter-badge">#{{ forloop.counter }}</span>
                    Extintor {% if form.instance.pk %}(Existente){% else %}(Nuevo){% endif %}
                </h5>
                <fieldset>
        <legend>Datos del Extintor</legend>
        {{ form.agente|as_crispy_field }}
        {{ form.nro_precinto|as_crispy_field }}
        {{ form.ubicacion|as_crispy_field }}
        {{ form.sello_incen|as_crispy_field }}
        {{ form.sello_incen_ste|as_crispy_field }}
        {{ form.certificado|as_crispy_field }}
    </fieldset>

    <fieldset>
        <legend>Estado General</legend>
        {{ form.estado|as_crispy_field }}
        {{ form.exterior|as_crispy_field }}
        {{ form.ph_ultima|as_crispy_field }}
        {{ form.ph_estado|as_crispy_field }}
        {{ form.ph_vencimiento|as_crispy_field }}
        {{ form.valvula|as_crispy_field }}
        {{ form.manometro|as_crispy_field }}
        {{ form.manguera|as_crispy_field }}
        {{ form.cintillo|as_crispy_field }}
        {{ form.agente_extintor|as_crispy_field }}
        {{ form.tubo_sifon|as_crispy_field }}
        {{ form.sellos_seguro|as_crispy_field }}
        {{ form.seguridad|as_crispy_field }}
        {{ form.rotulacion|as_crispy_field }}
        {{ form.ultima_fecha|as_crispy_field }}
    </fieldset>

    <fieldset>
        <legend>Verificación Técnica</legend>
        {{ form.recarga|as_crispy_field }}
        {{ form.mantencion|as_crispy_field }}
        {{ form.presion|as_crispy_field }}
        {{ form.peso|as_crispy_field }}
        {{ form.correcta|as_crispy_field }}
        {{ form.acceso|as_crispy_field }}
        {{ form.instrucciones|as_crispy_field }}
    </fieldset>

    <fieldset style="border: 2px solid red; padding: 1em; margin-top: 1em;">
        <legend style="font-weight: bold; color: red;">A criterio del Técnico</legend>
        {{ form.habilitado_un_ano|as_crispy_field }}
        {{ form.baja_por_oxido|as_crispy_field }}
        {{ form.baja_por_ph|as_crispy_field }}
    </fieldset>
            </div>
        {% endfor %}
    </div>

    <!-- Botón para agregar nuevos formularios -->
    <button type="button" class="btn btn-sm btn-primary mt-3" id="add-form">+ Agregar Extintor</button>

    <hr>
    <h4 class="mt-4">Fotografías del servicio (máximo 6)</h4>
    <div class="row">
        {{ imagenes_form.non_field_errors }}
        {% for field in imagenes_form %}
            <div class="col-md-4 mb-3">
                {{ field.label_tag }}
                {{ field }}
                {% if field.errors %}
                    <div class="text-danger small">{{ field.errors|join:", " }}</div>
                {% endif %}
            </div>
        {% endfor %}
    </div>

    <div class="d-flex justify-content-end gap-2 mt-4">
        <button class="btn btn-sm btn-success" type="submit">Guardar</button>
        <a href="{% url 'intervencion_lista' %}" class="btn btn-sm btn-warning">Regresar</a>
    </div>
</form>

<!-- Formulario vacío para clonar -->
<div id="empty-form" style="display: none;">
    <div class="card mt-3 p-3" style="background-color: #DCDCDC;" data-form-index="__prefix__">
        <h5 class="mb-3">
            <span class="counter-badge">#<span class="form-counter">__prefix__</span></span>
            Extintor (Nuevo)
        </h5>
        {{ formset.empty_form|crispy }}
    </div>
</div>

<script>
    document.getElementById('add-form').addEventListener('click', function () {
        const container = document.getElementById('form-container');
        const totalForms = document.getElementById('id_detalles-TOTAL_FORMS');
        const emptyFormHtml = document.getElementById('empty-form').innerHTML;
        const newFormIndex = parseInt(totalForms.value);

        // Reemplazar __prefix__ con el nuevo índice
        let newFormHtml = emptyFormHtml.replace(/__prefix__/g, newFormIndex);
        container.insertAdjacentHTML('beforeend', newFormHtml);

        // Actualizar el número visual dentro del badge
        const lastCard = container.lastElementChild;
        const counterBadge = lastCard.querySelector('.form-counter');
        if (counterBadge) {
            counterBadge.textContent = newFormIndex + 1;
        }

        // Actualizar TOTAL_FORMS
        totalForms.value = newFormIndex + 1;

    });
</script>
{% endblock %}

def crear_intervencion2(request):
    prefix = 'detalles'
    
    # Definir el formset aquí para usarlo consistentemente
    DetalleIntervencionFormSet = inlineformset_factory(
        Intervencion,
        DetalleIntervencion,
        form=DetalleIntervencionForm,
        extra=1,
        can_delete=True,
        validate_min=False
    )
    
    if request.method == 'POST':
        form = IntervencionForm(request.POST)
        formset = DetalleIntervencionFormSet(request.POST, prefix=prefix)
        imagenes_form = ImagenIntervencionForm(request.POST, request.FILES)
        
        # Validar TODOS los formularios juntos
        if all([form.is_valid(), formset.is_valid(), imagenes_form.is_valid()]):
            with transaction.atomic():
                # Guardar la intervención principal
                intervencion = form.save(commit=False)
                intervencion.save()  # Necesario para tener PK antes de relaciones
                
                # Guardar el formset de detalles
                instances = formset.save(commit=False)
                for instance in instances:
                    # Ignorar formularios vacíos (sin agente)
                    if not instance.agente:
                        continue
                    instance.intervencion = intervencion
                    instance.save()
                
                # Manejar objetos marcados para borrar (aunque en creación no debería haber)
                for obj in formset.deleted_objects:
                    obj.delete()
                
                # Guardar las imágenes
                imagen_instance = imagenes_form.save(commit=False)
                imagen_instance.intervencion = intervencion
                imagen_instance.save()
                
                # Crear ODT si aplica
                if intervencion.con_odt:
                    odt = Odt.objects.create(
                        intervencion=intervencion,
                        tecnico=intervencion.tecnico
                    )
                    
                    for d in intervencion.detalles.all():
                        DetalleOdt.objects.create(
                            odt=odt,
                            agente=d.agente,
                            nro_precinto=d.nro_precinto,
                            ubicacion=d.ubicacion,
                            sello_incen=d.sello_incen,
                            sello_incen_ste=d.sello_incen_ste,
                            certificado=d.certificado,
                            estado=d.estado,
                            exterior=d.exterior,
                            ph_ultima=d.ph_ultima,
                            ph_estado=d.ph_estado,
                            ph_vencimiento=d.ph_vencimiento,
                            valvula=d.valvula,
                            manometro=d.manometro,
                            manguera=d.manguera,
                            cintillo=d.cintillo,
                            agente_extintor=d.agente_extintor,
                            tubo_sifon=d.tubo_sifon,
                            sellos_seguro=d.sellos_seguro,
                            seguridad=d.seguridad,
                            rotulacion=d.rotulacion,
                            ultima_fecha=d.ultima_fecha,
                            recarga=d.recarga,
                            mantencion=d.mantencion,
                            presion=d.presion,
                            peso=d.peso,
                            correcta=d.correcta,
                            acceso=d.acceso,
                            instrucciones=d.instrucciones,
                            habilitado_un_ano=d.habilitado_un_ano,
                            baja_por_oxido=d.baja_por_oxido,
                            baja_por_ph=d.baja_por_ph,
                        )

                    registrar_bitacora(
                        usuario=request.user,
                        accion='Crear',
                        modelo='Odt',
                        objeto_id=odt.pk,  # Usar PK de la ODT creada
                        descripcion=f"El usuario {request.user.username} creó la ODT #{odt.pk} con fecha {odt.fecha.strftime('%Y-%m-%d')}."
                    )
                
                return redirect('intervencion_lista')
        else:
            # Manejo de errores detallado
            print("Formulario no válido")
            print("Errores en IntervencionForm:", form.errors)
            print("Errores en Formset:", formset.errors)
            print("Errores en ImagenIntervencionForm:", imagenes_form.errors)
    else:
        form = IntervencionForm()
        formset = DetalleIntervencionFormSet(prefix=prefix)
        imagenes_form = ImagenIntervencionForm()

    return render(request, 'intervenciones/crear.html', {
        'form': form,
        'formset': formset,
        'imagenes_form': imagenes_form,
        'prefix': prefix
    })


def crear_intervencion_ORIGINAL(request):
    prefix = 'detalles'
    if request.method == 'POST':
        form = IntervencionForm(request.POST)
        imagenes_form = ImagenIntervencionForm(request.POST, request.FILES)
        if form.is_valid() and imagenes_form.is_valid():
            intervencion = form.save()
            formset = DetalleIntervencionFormSet(request.POST, instance=intervencion, prefix=prefix)
            if formset.is_valid():
                formset.save()

                imagen_instance = imagenes_form.save(commit=False)
                imagen_instance.intervencion = intervencion
                imagen_instance.save()
                '''
                ImagenIntervencion.objects.create(
                    intervencion=intervencion,
                    imagen1=imagenes_form.cleaned_data.get('imagen1'),
                    imagen2=imagenes_form.cleaned_data.get('imagen2'),
                    imagen3=imagenes_form.cleaned_data.get('imagen3'),
                    imagen4=imagenes_form.cleaned_data.get('imagen4'),
                    imagen5=imagenes_form.cleaned_data.get('imagen5'),
                    imagen6=imagenes_form.cleaned_data.get('imagen6'),
                )
                '''
                imagen_instance = imagenes_form.save(commit=False)
                imagen_instance.intervencion = intervencion
                imagen_instance.save()


                if intervencion.con_odt and not hasattr(intervencion, 'odt_rel'):
                    odt = Odt.objects.create(intervencion=intervencion)
                    for d in intervencion.detalles.all():
                        DetalleOdt.objects.create(
                            odt=odt,
                            agente=d.agente,
                            nro_precinto=d.nro_precinto,
                            ubicacion=d.ubicacion,
                            sello_incen=d.sello_incen,
                            sello_incen_ste=d.sello_incen_ste,
                            certificado=d.certificado,
                            estado=d.estado,
                            exterior=d.exterior,
                            ph_ultima=d.ph_ultima,
                            ph_estado=d.ph_estado,
                            ph_vencimiento=d.ph_vencimiento,
                            valvula=d.valvula,
                            manometro=d.manometro,
                            manguera=d.manguera,
                            cintillo=d.cintillo,
                            agente_extintor=d.agente_extintor,
                            tubo_sifon=d.tubo_sifon,
                            sellos_seguro=d.sellos_seguro,
                            seguridad=d.seguridad,
                            rotulacion=d.rotulacion,
                            ultima_fecha=d.ultima_fecha,
                            recarga=d.recarga,
                            mantencion=d.mantencion,
                            presion=d.presion,
                            peso=d.peso,
                            correcta=d.correcta,
                            acceso=d.acceso,
                            instrucciones=d.instrucciones,
                            habilitado_un_ano = d.habilitado_un_ano,
                            baja_por_oxido = d.baja_por_oxido,
                            baja_por_ph = d.baja_por_ph,
                        )

                    registrar_bitacora(
                        usuario=request.user,
                        accion='Crear',
                        modelo='Odt',
                        objeto_id=pk,
                        descripcion = f"El usuario {request.user.username} creo la Odt #{odt.pk} con fecha {odt.fecha.strftime('%Y-%m-%d')}."
                        
                    )

                return redirect('intervencion_lista')
            else:
                # Manejar errores del formset
                pass
        else:
            # Manejar errores del formulario principal o de imágenes
            pass
    else:
        form = IntervencionForm()
        formset = DetalleIntervencionFormSet(prefix=prefix)
        imagenes_form = ImagenIntervencionForm()

    return render(request, 'intervenciones/crear.html', {
        'form': form,
        'formset': formset,
        'imagenes_form': imagenes_form,
        'prefix': prefix
    })



def editar_intervencion_con_falla(request, pk):
    intervencion = get_object_or_404(Intervencion, pk=pk)
    imagenes_instance = ImagenIntervencion.objects.filter(intervencion=intervencion).first()
    
    # Definimos el formset
    DetalleIntervencionFormSet = inlineformset_factory(
        Intervencion,
        DetalleIntervencion,
        form=DetalleIntervencionForm,
        extra=1,
        can_delete=True,
        validate_min=False
    )

    if request.method == 'POST':
        form = IntervencionForm(request.POST, instance=intervencion)
        formset = DetalleIntervencionFormSet(request.POST, instance=intervencion, prefix='detalles')
        imagenes_form = ImagenIntervencionForm(request.POST, request.FILES, instance=imagenes_instance)

        

        #if form.is_valid() and formset.is_valid() and imagenes_form.is_valid():
        if all([form.is_valid(), formset.is_valid(), imagenes_form.is_valid()]):
            intervencion = form.save()
            detalles_guardados = formset.save()

            print("Detalles guardados:", detalles_guardados)

            imagen_instance = imagenes_form.save(commit=False)
            imagen_instance.intervencion = intervencion
            imagen_instance.save()

            # Crear ODT si aplica y no existe aún
            if intervencion.con_odt and not hasattr(intervencion, 'odt_rel'):
                odt = Odt.objects.create(intervencion=intervencion, tecnico=intervencion.tecnico)
                for d in intervencion.detalles.all():
                    DetalleOdt.objects.create(
                        odt=odt,
                        agente=d.agente,
                        nro_precinto=d.nro_precinto,
                        ubicacion=d.ubicacion,
                        sello_incen=d.sello_incen,
                        sello_incen_ste=d.sello_incen_ste,
                        certificado=d.certificado,
                        estado=d.estado,
                        exterior=d.exterior,
                        ph_ultima=d.ph_ultima,
                        ph_estado=d.ph_estado,
                        ph_vencimiento=d.ph_vencimiento,
                        valvula=d.valvula,
                        manometro=d.manometro,
                        manguera=d.manguera,
                        cintillo=d.cintillo,
                        agente_extintor=d.agente_extintor,
                        tubo_sifon=d.tubo_sifon,
                        sellos_seguro=d.sellos_seguro,
                        seguridad=d.seguridad,
                        rotulacion=d.rotulacion,
                        ultima_fecha=d.ultima_fecha,
                        recarga=d.recarga,
                        mantencion=d.mantencion,
                        presion=d.presion,
                        peso=d.peso,
                        correcta=d.correcta,
                        acceso=d.acceso,
                        instrucciones=d.instrucciones,
                        habilitado_un_ano = d.habilitado_un_ano,
                        baja_por_oxido = d.baja_por_oxido,
                        baja_por_ph = d.baja_por_ph,
                    )

                registrar_bitacora(
                    usuario=request.user,
                    accion='Crear',
                    modelo='Odt',
                    objeto_id=intervencion.pk,
                    descripcion=f"El usuario {request.user.username} generó una ODT para la intervención #{intervencion.pk}."
                )

            return redirect('intervencion_detalle', pk=intervencion.pk)
        else:
            print("Formulario no válido")
            print("Errores en IntervencionForm:", form.errors)
            print("Errores en Formset:", formset.errors)
            print("Errores en ImagenIntervencionForm:", imagenes_form.errors)
    else:
        form = IntervencionForm(instance=intervencion)
        formset = DetalleIntervencionFormSet(instance=intervencion, prefix='detalles')
        imagenes_form = ImagenIntervencionForm(instance=imagenes_instance)

    context = {
        'form': form,
        'formset': formset,
        'imagenes_form': imagenes_form,
        'intervencion': intervencion,
    }
    return render(request, 'intervenciones/editar_intervencion.html', context)

